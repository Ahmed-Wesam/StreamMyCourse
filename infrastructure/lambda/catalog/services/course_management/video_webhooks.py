"""HTTP adapter for provider webhooks (Kinescope transcoding status)."""

from __future__ import annotations

import hmac
import logging
from typing import Any, Dict, Optional

from services.common.errors import HttpError
from services.common.http import json_response, options_response
from services.common.validation import parse_json_body
from services.course_management.service import CourseManagementService

logger = logging.getLogger(__name__)


def _api_error_response(exc: HttpError, origin: Optional[str]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return json_response(exc.status_code, payload, origin)


def _normalize_headers(event: Dict[str, Any]) -> Dict[str, str]:
    raw = event.get("headers") or {}
    if not isinstance(raw, dict):
        return {}
    return {str(k).lower(): str(v) for k, v in raw.items() if v is not None}


def _extract_webhook_secret(event: Dict[str, Any]) -> str:
    headers = _normalize_headers(event)
    header_val = headers.get("x-kinescope-webhook-secret", "").strip()
    qs = event.get("queryStringParameters") or {}
    query_val = ""
    if isinstance(qs, dict):
        query_val = str(qs.get("token") or qs.get("secret") or "").strip()
    return header_val or query_val


def _verify_webhook_secret(event: Dict[str, Any], configured_secret: str) -> bool:
    secret = (configured_secret or "").strip()
    if not secret:
        return True
    provided = _extract_webhook_secret(event)
    return hmac.compare_digest(provided, secret)


def handle_kinescope_webhook(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    svc: CourseManagementService,
    webhook_secret: str = "",
) -> Dict[str, Any]:
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    )
    if method == "OPTIONS":
        return options_response(origin)
    if method != "POST":
        return json_response(
            405,
            {"message": "Method not allowed", "code": "method_not_allowed"},
            origin,
        )

    if not _verify_webhook_secret(event, webhook_secret):
        return json_response(
            401,
            {"message": "Invalid webhook secret", "code": "unauthorized"},
            origin,
        )

    try:
        body = parse_json_body(event)
        result = svc.handle_kinescope_media_status(body)
        return json_response(200, result, origin)
    except HttpError as exc:
        return _api_error_response(exc, origin)
    except Exception:
        logger.exception("kinescope webhook handler failed")
        return json_response(
            500,
            {"message": "Webhook processing failed", "code": "internal_error"},
            origin,
        )


def handle_kinescope_drm_auth(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    svc: CourseManagementService,
) -> Dict[str, Any]:
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    )
    if method == "OPTIONS":
        return options_response(origin)
    if method != "POST":
        return json_response(
            405,
            {"message": "Method not allowed", "code": "method_not_allowed"},
            origin,
        )
    try:
        body = parse_json_body(event)
        allowed = svc.authorize_kinescope_drm(body)
        if allowed:
            return json_response(200, {"allow": True}, origin)
        return json_response(403, {"allow": False, "code": "forbidden"}, origin)
    except HttpError as exc:
        return _api_error_response(exc, origin)
    except Exception:
        logger.exception("kinescope drm-auth webhook handler failed")
        return json_response(
            403,
            {"allow": False, "code": "forbidden"},
            origin,
        )
