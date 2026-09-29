"""HTTP handlers for certificates (RS-12)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.certificates.service import CertificatesService
from services.common.errors import HttpError, NotFound, Unauthorized
from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
)

logger = logging.getLogger(__name__)


def _method_and_path(event: Dict[str, Any]) -> Tuple[str, str]:
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    )
    return method, apigw_routing_path(event)


def _actor_sub(claims: Dict[str, Any]) -> str:
    return str(claims.get("sub", "") or "").strip()


def _actor_role(claims: Dict[str, Any]) -> str:
    return str(claims.get("custom:role") or claims.get("role") or "student").strip().lower()


def _route(method: str, path: str) -> Tuple[str, Dict[str, str]]:
    parts = [p for p in path.split("/") if p]

    if method == "GET" and parts == ["me", "certificates"]:
        return "list_mine", {}

    if method == "GET" and len(parts) == 2 and parts[0] == "certificates":
        return "get_public", {"credentialId": parts[1]}

    if (
        method == "GET"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "certificates"
    ):
        return "list_course", {"courseId": parts[1]}

    if (
        method == "POST"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "certificates"
        and parts[4] == "revoke"
    ):
        return "revoke", {"courseId": parts[1], "certificateId": parts[3]}

    return "not_found", {}


def _is_certificates_route(method: str, path: str) -> bool:
    action, _ = _route(method, path)
    if action != "not_found":
        return True
    parts = [p for p in path.split("/") if p]
    if method == "OPTIONS":
        if parts == ["me", "certificates"]:
            return True
        if len(parts) == 2 and parts[0] == "certificates":
            return True
        if len(parts) == 3 and parts[0] == "courses" and parts[2] == "certificates":
            return True
        if (
            len(parts) == 5
            and parts[0] == "courses"
            and parts[2] == "certificates"
            and parts[4] == "revoke"
        ):
            return True
    return False


def _api_error_payload(exc: HttpError) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return payload


def handle_certificates_request(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    certificates_svc: CertificatesService,
) -> Optional[Dict[str, Any]]:
    """Handle certificate routes; return ``None`` when the request is not ours."""
    method, raw_path = _method_and_path(event)
    if not _is_certificates_route(method, raw_path):
        return None

    if method == "OPTIONS":
        return options_response(origin)

    action, params = _route(method, raw_path)
    if action == "not_found":
        return None

    try:
        if action == "get_public":
            try:
                result = certificates_svc.get_public(params["credentialId"])
                return json_response(200, result, origin)
            except NotFound:
                return json_response(
                    404,
                    certificates_svc.not_found_public_body(params["credentialId"]),
                    origin,
                )

        claims = apigw_cognito_claims(event)
        user_sub = _actor_sub(claims)
        role = _actor_role(claims)
        if not user_sub:
            raise Unauthorized("Authentication required")

        if action == "list_mine":
            result = certificates_svc.list_mine(user_sub=user_sub, role=role)
            return json_response(200, result, origin)

        if action == "list_course":
            result = certificates_svc.list_for_course(
                params["courseId"], cognito_sub=user_sub, role=role
            )
            return json_response(200, result, origin)

        if action == "revoke":
            result = certificates_svc.revoke(
                params["courseId"],
                params["certificateId"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        return None
    except HttpError as exc:
        logger.info(
            "Certificates HTTP error",
            extra={"status_code": exc.status_code, "error_code": exc.code},
        )
        return json_response(exc.status_code, _api_error_payload(exc), origin)
    except Exception:
        logger.exception("Unhandled certificates controller error")
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )
