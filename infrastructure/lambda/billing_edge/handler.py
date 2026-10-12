"""Billing edge Lambda — HyperPay checkout session/status (WS2 slim; webhooks deferred WS3)."""

from __future__ import annotations

import _vendor_bootstrap  # noqa: F401  # must precede cryptography (vendored in Lambda)

import base64
import json
import logging
from typing import Any, Dict

from cors import pick_origin
from domain.checkout_billing import parse_checkout_billing
from catalog_invoke import (
    CatalogInvokeError,
    invoke_billing_checkout,
    invoke_billing_checkout_rollback,
    invoke_billing_checkout_status,
)
from edge_config import BillingEdgeConfig, get_payment_provider, load_billing_edge_config
from providers.hyperpay_adapter import BillingUnconfiguredError
from providers.port import CheckoutProduct, PaymentProviderPort

logger = logging.getLogger(__name__)

_load_config = load_billing_edge_config
_get_payment_provider = get_payment_provider
_invoke_billing_checkout = invoke_billing_checkout
_invoke_billing_checkout_rollback = invoke_billing_checkout_rollback
_invoke_billing_checkout_status = invoke_billing_checkout_status

_MANAGE_CONFLICT_MESSAGES: Dict[str, str] = {
    "already_owned": "You already own this course or bundle",
    "not_found": "Purchase not found or not authorized",
    "amount_mismatch": "Payment amount does not match the pending purchase",
}

_BILLING_MANAGE_POST_PATHS = frozenset({"/billing/checkout-session", "/billing/checkout-status"})

_BILLING_MANAGE_OPTIONS_PATHS = frozenset({"/billing/checkout-session", "/billing/checkout-status"})

_CSP_API = "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def _request_origin(event: Dict[str, Any]) -> str:
    headers = event.get("headers") or {}
    if isinstance(headers, dict):
        return _header_lookup(headers, "Origin")
    return ""


def _json_response(
    status_code: int,
    body: Dict[str, Any],
    *,
    cors_origin: str | None = None,
) -> Dict[str, Any]:
    headers: Dict[str, str] = {
        "content-type": "application/json",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": _CSP_API,
        "Cache-Control": "no-store",
    }
    if cors_origin:
        headers["Access-Control-Allow-Origin"] = cors_origin
        headers["Access-Control-Allow-Methods"] = "POST,OPTIONS"
        headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        if cors_origin.startswith("https://"):
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }


def _error_response(
    status_code: int,
    code: str,
    message: str,
    *,
    cors_origin: str | None = None,
) -> Dict[str, Any]:
    return _json_response(status_code, {"code": code, "message": message}, cors_origin=cors_origin)


def _cors_origin_for_manage(event: Dict[str, Any], cfg: BillingEdgeConfig) -> str | None:
    return pick_origin(list(cfg.allowed_origins), _request_origin(event) or None)


def _manage_conflict_response(
    error_code: str,
    *,
    cors_origin: str | None = None,
) -> Dict[str, Any]:
    message = _MANAGE_CONFLICT_MESSAGES.get(
        error_code,
        "Checkout cannot proceed in the current state",
    )
    return _error_response(409, error_code, message, cors_origin=cors_origin)


def _options_response(event: Dict[str, Any], cfg: BillingEdgeConfig) -> Dict[str, Any]:
    cors_origin = _cors_origin_for_manage(event, cfg)
    response_headers: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": _CSP_API,
    }
    if cors_origin:
        response_headers["Access-Control-Allow-Origin"] = cors_origin
        response_headers["Access-Control-Allow-Methods"] = "POST,OPTIONS"
        response_headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        if cors_origin.startswith("https://"):
            response_headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return {
        "statusCode": 204,
        "headers": response_headers,
        "body": "",
    }


def _apigw_routing_path(event: Dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    resource_path = rc.get("resourcePath")
    if isinstance(resource_path, str) and resource_path.startswith("/"):
        return resource_path
    path = event.get("path")
    if isinstance(path, str) and path.startswith("/"):
        return path
    raw = event.get("rawPath")
    if isinstance(raw, str) and raw.startswith("/"):
        return raw
    return "/"


def _header_lookup(headers: Dict[str, Any], name: str) -> str:
    if not isinstance(headers, dict):
        return ""
    target = name.lower()
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == target and value is not None:
            return str(value).strip()
    return ""


def _raw_body_bytes(event: Dict[str, Any]) -> bytes:
    body = event.get("body")
    if body is None:
        return b""
    if not isinstance(body, str):
        return b""
    if event.get("isBase64Encoded"):
        return base64.b64decode(body)
    return body.encode("utf-8")


def _claims_email(event: Dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    authorizer = rc.get("authorizer") if isinstance(rc, dict) else {}
    if not isinstance(authorizer, dict):
        return ""
    claims = authorizer.get("claims")
    if isinstance(claims, dict):
        return str(claims.get("email") or "").strip()
    if isinstance(claims, str) and claims.strip():
        try:
            parsed = json.loads(claims)
            if isinstance(parsed, dict):
                return str(parsed.get("email") or "").strip()
        except json.JSONDecodeError:
            pass
    return ""


def _claims_sub(event: Dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    authorizer = rc.get("authorizer") if isinstance(rc, dict) else {}
    if not isinstance(authorizer, dict):
        return ""
    claims = authorizer.get("claims")
    if isinstance(claims, dict):
        return str(claims.get("sub") or "").strip()
    if isinstance(claims, str) and claims.strip():
        try:
            parsed = json.loads(claims)
            if isinstance(parsed, dict):
                return str(parsed.get("sub") or "").strip()
        except json.JSONDecodeError:
            pass
    return str(authorizer.get("sub") or "").strip()


def _request_id(event: Dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    if isinstance(rc, dict):
        rid = rc.get("requestId")
        if rid:
            return str(rid)
    return ""


def _checkout_id_prefix(checkout_id: str) -> str:
    normalized = (checkout_id or "").strip()
    if len(normalized) <= 16:
        return normalized
    return f"{normalized[:16]}…"


def _parse_checkout_product(
    product_payload: Any,
    *,
    product_type: str,
) -> tuple[CheckoutProduct, str, str | None] | None:
    if not isinstance(product_payload, dict):
        return None
    normalized_type = (product_type or "").strip().lower()
    if normalized_type not in ("course", "bundle"):
        return None
    amount_raw = product_payload.get("amount_minor")
    currency = str(product_payload.get("currency") or "").strip().upper()
    purchase_id = str(
        product_payload.get("purchase_id") or product_payload.get("purchaseId") or ""
    ).strip()
    course_id_raw = product_payload.get("course_id") or product_payload.get("courseId")
    course_id = str(course_id_raw).strip() if course_id_raw is not None else None
    if amount_raw is None or currency != "JOD" or not purchase_id:
        return None
    try:
        amount_minor = int(amount_raw)
    except (TypeError, ValueError):
        return None
    if amount_minor <= 0:
        return None
    description = normalized_type
    if normalized_type == "course" and course_id:
        description = f"course:{course_id}"
    return (
        CheckoutProduct(
            amount_minor=amount_minor,
            currency=currency,
            description=description,
        ),
        purchase_id,
        course_id if normalized_type == "course" else None,
    )


def _parse_checkout_request(
    raw: bytes,
) -> tuple[str, str | None, Any] | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    product_type = str(payload.get("productType") or payload.get("product_type") or "").strip().lower()
    if product_type not in ("course", "bundle"):
        return None
    course_id: str | None = None
    if product_type == "course":
        course_id = str(payload.get("courseId") or payload.get("course_id") or "").strip()
        if not course_id:
            return None
    try:
        billing = parse_checkout_billing(payload.get("billing"))
    except ValueError as exc:
        return ("__billing_error__", str(exc), None)
    return product_type, course_id, billing


def _parse_checkout_status_purchase_id(raw: bytes) -> str | None:
    """Return purchaseId when present; None when purchaseId is missing (incl. checkoutId-only)."""
    if not raw:
        return None
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    purchase_id = str(payload.get("purchaseId") or payload.get("purchase_id") or "").strip()
    if purchase_id:
        return purchase_id
    return None


def _handle_checkout(
    event: Dict[str, Any],
    provider: PaymentProviderPort,
    cfg: BillingEdgeConfig,
) -> Dict[str, Any]:
    cors = _cors_origin_for_manage(event, cfg)
    user_sub = _claims_sub(event)
    if not user_sub:
        return _error_response(401, "unauthorized", "Missing authenticated user", cors_origin=cors)

    raw = _raw_body_bytes(event)
    parsed_request = _parse_checkout_request(raw)
    if parsed_request is None:
        if raw:
            try:
                json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return _error_response(400, "invalid_request", "Invalid JSON body", cors_origin=cors)
        return _error_response(
            400,
            "invalid_request",
            "productType is required (course or bundle); courseId required for course",
            cors_origin=cors,
        )

    product_type, course_id, billing = parsed_request
    if product_type == "__billing_error__":
        return _error_response(400, "invalid_request", str(course_id or "Invalid billing"), cors_origin=cors)

    customer_email = _claims_email(event)
    if not customer_email:
        return _error_response(
            400,
            "invalid_request",
            "Authenticated user email is required for checkout",
            cors_origin=cors,
        )

    catalog_arn = str(cfg.catalog_lambda_arn or "").strip()
    if not catalog_arn:
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)

    if not (cfg.billing_shopper_result_url or "").strip():
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)

    try:
        precheck = _invoke_billing_checkout(
            user_sub=user_sub,
            product_type=product_type,
            course_id=course_id,
            catalog_lambda_arn=catalog_arn,
        )
    except CatalogInvokeError:
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)

    block_reason = precheck.get("blockReason")
    if block_reason == "already_owned":
        logger.info(
            "checkout_session_blocked requestId=%s block_reason=already_owned product_type=%s",
            _request_id(event),
            product_type,
        )
        return _manage_conflict_response("already_owned", cors_origin=cors)
    if block_reason == "checkout_in_progress":
        logger.info(
            "checkout_session_blocked requestId=%s block_reason=checkout_in_progress product_type=%s",
            _request_id(event),
            product_type,
        )
        return _error_response(
            409,
            "checkout_in_progress",
            (
                "A checkout is already in progress. "
                "Wait a moment or try again shortly."
            ),
            cors_origin=cors,
        )

    parsed_product = _parse_checkout_product(
        precheck.get("product"),
        product_type=product_type,
    )
    if parsed_product is None:
        _invoke_billing_checkout_rollback(
            user_sub=user_sub,
            product_type=product_type,
            course_id=course_id,
            catalog_lambda_arn=catalog_arn,
        )
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)

    checkout_product, purchase_id, product_course_id = parsed_product
    sale_course_id = course_id or product_course_id

    try:
        session = provider.create_checkout(
            user_sub=user_sub,
            purchase_id=purchase_id,
            product_type=product_type,
            course_id=sale_course_id,
            product=checkout_product,
            customer_email=customer_email,
            billing=billing,
        )
    except BillingUnconfiguredError:
        _invoke_billing_checkout_rollback(
            user_sub=user_sub,
            product_type=product_type,
            course_id=course_id,
            catalog_lambda_arn=catalog_arn,
        )
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)
    except NotImplementedError:
        _invoke_billing_checkout_rollback(
            user_sub=user_sub,
            product_type=product_type,
            course_id=course_id,
            catalog_lambda_arn=catalog_arn,
        )
        return _error_response(501, "not_implemented", "Checkout is not implemented yet", cors_origin=cors)

    logger.info(
        "checkout_session_created requestId=%s purchase_id=%s checkout_id_prefix=%s "
        "product_type=%s amount_minor=%s currency=%s",
        _request_id(event),
        purchase_id,
        _checkout_id_prefix(session.checkout_id),
        product_type,
        checkout_product.amount_minor,
        checkout_product.currency,
    )

    return _json_response(
        200,
        {
            "checkoutId": session.checkout_id,
            "integrity": session.integrity,
            "widgetScriptUrl": session.widget_url,
            "shopperResultUrl": cfg.billing_shopper_result_url,
            "purchaseId": purchase_id,
            "amountMinor": checkout_product.amount_minor,
            "currency": checkout_product.currency,
        },
        cors_origin=cors,
    )


def _handle_checkout_status(
    event: Dict[str, Any],
    _provider: PaymentProviderPort,
    cfg: BillingEdgeConfig,
) -> Dict[str, Any]:
    cors = _cors_origin_for_manage(event, cfg)
    user_sub = _claims_sub(event)
    if not user_sub:
        return _error_response(401, "unauthorized", "Missing authenticated user", cors_origin=cors)

    raw = _raw_body_bytes(event)
    purchase_id = _parse_checkout_status_purchase_id(raw)
    if not purchase_id:
        return _error_response(
            400,
            "invalid_request",
            "purchaseId is required",
            cors_origin=cors,
        )

    catalog_arn = str(cfg.catalog_lambda_arn or "").strip()
    if not catalog_arn:
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)

    try:
        result = _invoke_billing_checkout_status(
            user_sub=user_sub,
            purchase_id=purchase_id,
            amount_minor=None,
            currency=None,
            catalog_lambda_arn=catalog_arn,
        )
    except CatalogInvokeError:
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)

    block = result.get("blockReason")
    if block == "not_found":
        return _error_response(
            404,
            "not_found",
            _MANAGE_CONFLICT_MESSAGES["not_found"],
            cors_origin=cors,
        )
    if block in _MANAGE_CONFLICT_MESSAGES:
        return _manage_conflict_response(str(block), cors_origin=cors)
    if block:
        return _error_response(403, "forbidden", "Purchase not authorized", cors_origin=cors)

    status = result.get("status")
    if not isinstance(status, str) or not status.strip():
        return _error_response(503, "billing_unconfigured", "Billing is not configured", cors_origin=cors)

    logger.info(
        "checkout_status_catalog requestId=%s purchase_id=%s status=%s",
        _request_id(event),
        purchase_id,
        status,
    )
    return _json_response(200, {"status": status.strip()}, cors_origin=cors)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway proxy entry point."""
    logging.getLogger().setLevel(logging.INFO)
    _ = context

    cfg = _load_config()
    method = (event.get("httpMethod") or "").upper()
    path = _apigw_routing_path(event)

    if method == "OPTIONS" and path in _BILLING_MANAGE_OPTIONS_PATHS:
        return _options_response(event, cfg)

    if method == "POST" and path == "/webhooks/payments/hyperpay":
        return _error_response(404, "not_found", "Not found")

    provider = _get_payment_provider(cfg)

    if provider is None:
        if path in _BILLING_MANAGE_POST_PATHS:
            return _error_response(
                503,
                "billing_unconfigured",
                "Billing is not configured",
                cors_origin=_cors_origin_for_manage(event, cfg),
            )
        return _error_response(404, "not_found", "Not found")

    if method == "POST" and path == "/billing/checkout-session":
        return _handle_checkout(event, provider, cfg)
    if method == "POST" and path == "/billing/checkout-status":
        return _handle_checkout_status(event, provider, cfg)

    return _error_response(404, "not_found", "Not found")
