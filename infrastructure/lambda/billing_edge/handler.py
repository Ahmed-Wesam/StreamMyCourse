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
from edge_config import BillingEdgeConfig, get_payment_provider, load_billing_edge_config
from providers.mock_adapter import MockPayTabsAdapter
from providers.paytabs_adapter import BillingUnconfiguredError, PayTabsAdapter
from providers.port import PaymentProviderPort
from queue_shim import EnqueueError, enqueue_domain_events

logger = logging.getLogger(__name__)

_load_config = load_billing_edge_config
_get_payment_provider = get_payment_provider
_enqueue_domain_events = enqueue_domain_events

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


def _handle_checkout(
    event: Dict[str, Any],
    provider: PaymentProviderPort,
) -> Dict[str, Any]:
    user_sub = _claims_sub(event)
    if not user_sub:
        return _error_response(401, "unauthorized", "Missing authenticated user")

    plan_id = ""
    raw = _raw_body_bytes(event)
    if raw:
        try:
            payload = json.loads(raw.decode("utf-8"))
            if isinstance(payload, dict):
                plan_id = str(payload.get("planId") or payload.get("plan_id") or "").strip()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error_response(400, "invalid_request", "Invalid JSON body")

    if not plan_id:
        return _error_response(400, "invalid_request", "planId is required")

    try:
        session = provider.create_subscribe_session(user_sub=user_sub, plan_id=plan_id)
    except BillingUnconfiguredError:
        return _error_response(503, "billing_unconfigured", "Billing is not configured")
    except NotImplementedError:
        return _error_response(501, "not_implemented", "Checkout is not implemented yet")

    return _json_response(200, {"redirect_url": session.redirect_url})


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
    if provider is None:
        path = _apigw_routing_path(event)
        if path in ("/billing/checkout-session", "/webhooks/payments/paytabs"):
            return _error_response(503, "billing_unconfigured", "Billing is not configured")
        return _error_response(404, "not_found", "Not found")

    method = (event.get("httpMethod") or "").upper()
    path = _apigw_routing_path(event)

    if method == "OPTIONS" and path == "/billing/checkout-session":
        return _options_response(event)

    if method == "POST" and path == "/billing/checkout-session":
        return _handle_checkout(event, provider)
    if method == "POST" and path == "/webhooks/payments/paytabs":
        return _handle_webhook(event, provider, cfg)

    return _error_response(404, "not_found", "Not found")
