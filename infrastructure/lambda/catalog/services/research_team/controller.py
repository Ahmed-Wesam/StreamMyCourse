"""HTTP handlers for research team (RS-14)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.common.errors import HttpError, Unauthorized
from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
)
from services.common.validation import parse_json_body
from services.research_team.service import ResearchTeamService

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

    if method == "GET" and parts == ["research-team", "requirements"]:
        return "get_requirements", {}

    if (
        method == "PUT"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "research-team-requirement"
    ):
        return "put_requirement", {"courseId": parts[1]}

    if (
        method == "GET"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "research-team-requirement"
    ):
        return "get_requirement", {"courseId": parts[1]}

    if method == "GET" and parts == ["me", "research-team"]:
        return "get_me", {}

    if method == "POST" and parts == ["me", "research-team", "applications"]:
        return "submit", {}

    if method == "GET" and parts == ["research-team", "applications"]:
        return "list_applications", {}

    if (
        method == "GET"
        and len(parts) == 3
        and parts[0] == "research-team"
        and parts[1] == "applications"
    ):
        return "get_application", {"id": parts[2]}

    if (
        method == "PATCH"
        and len(parts) == 3
        and parts[0] == "research-team"
        and parts[1] == "applications"
    ):
        return "patch_application", {"id": parts[2]}

    if (
        method == "POST"
        and len(parts) == 4
        and parts[0] == "research-team"
        and parts[1] == "applications"
        and parts[3] == "allow-reapply"
    ):
        return "allow_reapply", {"id": parts[2]}

    return "not_found", {}


def _is_research_team_route(method: str, path: str) -> bool:
    action, _ = _route(method, path)
    if action != "not_found":
        return True
    if method != "OPTIONS":
        return False
    parts = [p for p in path.split("/") if p]
    if parts == ["research-team", "requirements"]:
        return True
    if parts == ["me", "research-team"]:
        return True
    if parts == ["me", "research-team", "applications"]:
        return True
    if parts == ["research-team", "applications"]:
        return True
    if len(parts) == 3 and parts[0] == "research-team" and parts[1] == "applications":
        return True
    if (
        len(parts) == 4
        and parts[0] == "research-team"
        and parts[1] == "applications"
        and parts[3] == "allow-reapply"
    ):
        return True
    if (
        len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "research-team-requirement"
    ):
        return True
    return False


def _api_error_payload(exc: HttpError) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return payload


def handle_research_team_request(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    research_team_svc: ResearchTeamService,
) -> Optional[Dict[str, Any]]:
    """Handle research-team routes; return ``None`` when the request is not ours."""
    method, raw_path = _method_and_path(event)
    if not _is_research_team_route(method, raw_path):
        return None

    if method == "OPTIONS":
        return options_response(origin)

    action, params = _route(method, raw_path)
    if action == "not_found":
        return None

    try:
        if action == "get_requirements":
            return json_response(200, research_team_svc.get_requirements(), origin)

        claims = apigw_cognito_claims(event)
        user_sub = _actor_sub(claims)
        role = _actor_role(claims)
        if not user_sub:
            raise Unauthorized("Authentication required")

        if action == "put_requirement":
            body = parse_json_body(event) if event.get("body") else {}
            result = research_team_svc.set_requirement(
                params["courseId"], body, role=role
            )
            return json_response(200, result, origin)

        if action == "get_requirement":
            result = research_team_svc.get_requirement(params["courseId"], role=role)
            return json_response(200, result, origin)

        if action == "get_me":
            result = research_team_svc.get_me(user_sub=user_sub, role=role)
            return json_response(200, result, origin)

        if action == "submit":
            body = parse_json_body(event) if event.get("body") else {}
            result = research_team_svc.submit(body, user_sub=user_sub, role=role)
            return json_response(201, result, origin)

        if action == "list_applications":
            result = research_team_svc.list_applications(role=role)
            return json_response(200, result, origin)

        if action == "get_application":
            result = research_team_svc.get_application(params["id"], role=role)
            return json_response(200, result, origin)

        if action == "patch_application":
            body = parse_json_body(event) if event.get("body") else {}
            result = research_team_svc.patch_application(
                params["id"], body, role=role
            )
            return json_response(200, result, origin)

        if action == "allow_reapply":
            result = research_team_svc.allow_reapply(params["id"], role=role)
            return json_response(200, result, origin)

        return None
    except HttpError as exc:
        logger.info(
            "Research team HTTP error",
            extra={
                "status_code": exc.status_code,
                "error_code": exc.code,
                "action": action,
            },
        )
        return json_response(exc.status_code, _api_error_payload(exc), origin)
    except Exception:
        logger.exception("Unhandled research team controller error")
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )
