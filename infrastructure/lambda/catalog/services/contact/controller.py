"""HTTP adapter for public POST /contact."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.common.errors import BadRequest, HttpError
from services.common.http import apigw_routing_path, json_response, options_response
from services.common.validation import parse_json_body
from services.contact.service import ContactService

logger = logging.getLogger(__name__)

_MAX_BODY_BYTES = 16 * 1024


def _api_error_payload(exc: HttpError) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return payload


def _api_error_response(exc: HttpError, origin: Optional[str]) -> Dict[str, Any]:
    return json_response(exc.status_code, _api_error_payload(exc), origin)


def _method_and_path(event: Dict[str, Any]) -> Tuple[str, str]:
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    )
    return method, apigw_routing_path(event)


def _raw_body_byte_length(event: Dict[str, Any]) -> int:
    raw_body = event.get("body")
    if raw_body is None:
        return 0
    if isinstance(raw_body, str):
        return len(raw_body.encode("utf-8"))
    if isinstance(raw_body, (bytes, bytearray)):
        return len(raw_body)
    return len(str(raw_body).encode("utf-8"))


def _is_contact_route(method: str, raw_path: str) -> bool:
    parts = [p for p in raw_path.split("/") if p]
    return method in ("POST", "OPTIONS") and parts == ["contact"]


def handle_contact_request(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    contact_svc: ContactService,
) -> Optional[Dict[str, Any]]:
    """Handle POST /contact; return ``None`` when the request is not ours."""
    method, raw_path = _method_and_path(event)
    if not _is_contact_route(method, raw_path):
        return None

    if method == "OPTIONS":
        return options_response(origin)

    try:
        if _raw_body_byte_length(event) > _MAX_BODY_BYTES:
            raise BadRequest("Request body is too large")
        body = parse_json_body(event)
        contact_svc.submit_from_dict(body)
        return json_response(202, {"accepted": True}, origin)
    except HttpError as exc:
        logger.info(
            "Contact HTTP error",
            extra={"status_code": exc.status_code, "error_code": exc.code},
        )
        return _api_error_response(exc, origin)
    except Exception:
        logger.exception("Unhandled contact controller error")
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )
