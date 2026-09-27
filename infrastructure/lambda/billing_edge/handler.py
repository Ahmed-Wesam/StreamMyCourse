"""Billing edge Lambda — checkout session + PayTabs IPN webhook (WS2/WS3)."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any, Dict

from domain.metadata import (
    EnvironmentMismatchError,
    InvalidCartMetadataError,
    MissingSubscriptionPeriodError,
)
from catalog_invoke import (
    CatalogInvokeError,
    invoke_billing_checkout,
    invoke_billing_checkout_rollback,
)
from edge_config import BillingEdgeConfig, get_payment_provider, load_billing_edge_config
from providers.mock_adapter import MockPayTabsAdapter
from providers.paytabs_adapter import BillingUnconfiguredError, PayTabsAdapter
from providers.port import CheckoutProduct, PaymentProviderPort
from queue_shim import EnqueueError, enqueue_domain_events

logger = logging.getLogger(__name__)

_load_config = load_billing_edge_config
_get_payment_provider = get_payment_provider
_enqueue_domain_events = enqueue_domain_events
_invoke_billing_checkout = invoke_billing_checkout
_invoke_billing_checkout_rollback = invoke_billing_checkout_rollback

_MANAGE_CONFLICT_MESSAGES: Dict[str, str] = {
    "already_owned": "You already own this course or bundle",
}

_BILLING_MANAGE_POST_PATHS = frozenset({"/billing/checkout-session"})

_BILLING_MANAGE_OPTIONS_PATHS = frozenset({"/billing/checkout-session"})

_CSP_API = "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


def _json_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": _CSP_API,
            "Cache-Control": "no-store",
        },
        "body": json.dumps(body),
    }


def _error_response(status_code: int, code: str, message: str) -> Dict[str, Any]:
    return _json_response(status_code, {"code": code, "message": message})


def _manage_conflict_response(error_code: str) -> Dict[str, Any]:
    message = _MANAGE_CONFLICT_MESSAGES.get(
        error_code,
        "Checkout cannot proceed in the current state",
    )
    return _error_response(409, error_code, message)


def _options_response(event: Dict[str, Any]) -> Dict[str, Any]:
    headers = event.get("headers") or {}
    origin = _header_lookup(headers, "Origin") if isinstance(headers, dict) else ""
    response_headers: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": _CSP_API,
    }
    if origin:
        response_headers["Access-Control-Allow-Origin"] = origin
        response_headers["Access-Control-Allow-Methods"] = "POST,OPTIONS"
        response_headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        if origin.startswith("https://"):
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
    if amount_raw is None or currency != "USD" or not purchase_id:
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


def _parse_checkout_request(raw: bytes) -> tuple[str, str | None] | None:
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
    return product_type, course_id


def _handle_checkout(
    event: Dict[str, Any],
    provider: PaymentProviderPort,
    cfg: BillingEdgeConfig,
) -> Dict[str, Any]:
    user_sub = _claims_sub(event)
    if not user_sub:
        return _error_response(401, "unauthorized", "Missing authenticated user")

    raw = _raw_body_bytes(event)
    parsed_request = _parse_checkout_request(raw)
    if parsed_request is None:
        if raw:
            try:
                json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return _error_response(400, "invalid_request", "Invalid JSON body")
        return _error_response(
            400,
            "invalid_request",
            "productType is required (course or bundle); courseId required for course",
        )

    product_type, course_id = parsed_request

    catalog_arn = str(cfg.catalog_lambda_arn or "").strip()
    if not catalog_arn:
        return _error_response(503, "billing_unconfigured", "Billing is not configured")

    if isinstance(provider, PayTabsAdapter):
        if not (cfg.billing_return_success_url or "").strip() or not (
            cfg.billing_ipn_callback_url or ""
        ).strip():
            return _error_response(503, "billing_unconfigured", "Billing is not configured")

    try:
        precheck = _invoke_billing_checkout(
            user_sub=user_sub,
            product_type=product_type,
            course_id=course_id,
            catalog_lambda_arn=catalog_arn,
        )
    except CatalogInvokeError:
        return _error_response(503, "billing_unconfigured", "Billing is not configured")

    block_reason = precheck.get("blockReason")
    if block_reason == "already_owned":
        return _manage_conflict_response("already_owned")
    if block_reason == "checkout_in_progress":
        return _error_response(
            409,
            "checkout_in_progress",
            (
                "A checkout is already in progress. "
                "Wait a moment or try again shortly."
            ),
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
        return _error_response(503, "billing_unconfigured", "Billing is not configured")

    checkout_product, purchase_id, product_course_id = parsed_product
    sale_course_id = course_id or product_course_id

    try:
        session = provider.create_sale_session(
            user_sub=user_sub,
            purchase_id=purchase_id,
            product_type=product_type,
            course_id=sale_course_id,
            product=checkout_product,
        )
    except BillingUnconfiguredError:
        _invoke_billing_checkout_rollback(
            user_sub=user_sub,
            product_type=product_type,
            course_id=course_id,
            catalog_lambda_arn=catalog_arn,
        )
        return _error_response(503, "billing_unconfigured", "Billing is not configured")
    except NotImplementedError:
        _invoke_billing_checkout_rollback(
            user_sub=user_sub,
            product_type=product_type,
            course_id=course_id,
            catalog_lambda_arn=catalog_arn,
        )
        return _error_response(501, "not_implemented", "Checkout is not implemented yet")

    return _json_response(
        200,
        {
            "redirect_url": session.redirect_url,
            "purchaseId": purchase_id,
            "amountMinor": checkout_product.amount_minor,
            "currency": checkout_product.currency,
        },
    )


def _webhook_signature_header(event: Dict[str, Any], provider: PaymentProviderPort) -> str:
    headers = event.get("headers") or {}
    if isinstance(provider, MockPayTabsAdapter):
        return _header_lookup(headers, "X-Mock-Signature")
    return _header_lookup(headers, "Signature")


def _webhook_server_key(provider: PaymentProviderPort, cfg: BillingEdgeConfig) -> str:
    if isinstance(provider, PayTabsAdapter):
        return provider.server_key
    return cfg.paytabs_server_key or ""


def _handle_webhook(
    event: Dict[str, Any],
    provider: PaymentProviderPort,
    cfg: BillingEdgeConfig,
) -> Dict[str, Any]:
    raw = _raw_body_bytes(event)
    signature = _webhook_signature_header(event, provider)
    server_key = _webhook_server_key(provider, cfg)

    if not provider.verify_webhook(raw, signature, server_key):
        return _error_response(401, "invalid_signature", "Invalid webhook signature")

    payload_digest = hashlib.sha256(raw).hexdigest()
    request_id = _request_id(event)

    try:
        events = provider.parse_webhook(
            raw,
            deployment_environment=cfg.deployment_environment,
            payload_digest=payload_digest,
        )
    except EnvironmentMismatchError:
        return _error_response(400, "environment_mismatch", "IPN environment does not match deployment")
    except InvalidCartMetadataError as exc:
        return _error_response(400, "invalid_cart_metadata", str(exc))
    except MissingSubscriptionPeriodError as exc:
        return _error_response(400, "missing_subscription_period", str(exc))

    if not events:
        logger.info(
            "webhook_no_domain_events requestId=%s digest_prefix=%s",
            request_id,
            payload_digest[:12],
        )
        return _json_response(200, {"status": "ok"})

    queue_url = cfg.fulfillment_queue_url or ""
    try:
        _enqueue_domain_events(events, queue_url=queue_url)
    except EnqueueError:
        logger.exception(
            "webhook_enqueue_failed requestId=%s event_count=%s",
            request_id,
            len(events),
        )
        return _error_response(500, "enqueue_failed", "Failed to enqueue billing events")

    for domain_event in events:
        logger.info(
            "webhook_enqueued requestId=%s provider_event_id=%s event_type=%s",
            request_id,
            domain_event.provider_event_id,
            domain_event.event_type,
        )

    return _json_response(200, {"status": "ok"})


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway proxy entry point."""
    logging.getLogger().setLevel(logging.INFO)
    _ = context

    cfg = _load_config()
    provider = _get_payment_provider(cfg)
    method = (event.get("httpMethod") or "").upper()
    path = _apigw_routing_path(event)

    if provider is None:
        if path in _BILLING_MANAGE_POST_PATHS or path == "/webhooks/payments/paytabs":
            return _error_response(503, "billing_unconfigured", "Billing is not configured")
        return _error_response(404, "not_found", "Not found")

    if method == "OPTIONS" and path in _BILLING_MANAGE_OPTIONS_PATHS:
        return _options_response(event)

    if method == "POST" and path == "/billing/checkout-session":
        return _handle_checkout(event, provider, cfg)
    if method == "POST" and path == "/webhooks/payments/paytabs":
        return _handle_webhook(event, provider, cfg)

    return _error_response(404, "not_found", "Not found")
