from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple

from services.common.errors import HttpError
from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
)
from services.common.jwt_verify import CognitoJwtConfig
from services.common.runtime_context import update_action
from services.common.validation import optional_bool, optional_int, parse_json_body
from services.progress.service import LessonProgressService

logger = logging.getLogger(__name__)


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


def _jwt_claims(
    event: Dict[str, Any],
    jwt_config: Optional[CognitoJwtConfig] = None,
) -> Dict[str, Any]:
    return apigw_cognito_claims(event, jwt_config=jwt_config)


def _actor_sub(claims: Dict[str, Any]) -> str:
    return str(claims.get("sub", "") or "").strip()


def _actor_role(claims: Dict[str, Any]) -> str:
    return str(claims.get("custom:role") or claims.get("role") or "student").strip().lower()


def _route(method: str, path: str) -> Tuple[str, Dict[str, str]]:
    parts = [p for p in path.split("/") if p]
    if (
        method == "GET"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "progress"
    ):
        return "get_course_progress", {"courseId": parts[1]}
    if (
        method == "PUT"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "lessons"
        and parts[4] == "progress"
    ):
        return "put_lesson_progress", {"courseId": parts[1], "lessonId": parts[3]}
    return "not_found", {}


def handle(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    progress_svc: LessonProgressService,
    auth_enforced: bool,
    jwt_config: Optional[CognitoJwtConfig] = None,
) -> Dict[str, Any]:
    method, raw_path = _method_and_path(event)
    if method == "OPTIONS":
        return options_response(origin)

    action, params = _route(method, raw_path)
    update_action(action)
    claims = _jwt_claims(event, jwt_config=jwt_config)

    try:
        if action == "get_course_progress":
            body = progress_svc.get_course_progress(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            return json_response(200, body, origin)
        if action == "put_lesson_progress":
            req = parse_json_body(event)
            last_pos = optional_int(req, "lastPositionSec")
            mark_complete = optional_bool(req, "markComplete") or False
            mark_incomplete = optional_bool(req, "markIncomplete") or False
            body = progress_svc.update_lesson_progress(
                params["courseId"],
                params["lessonId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
                last_position_sec=last_pos,
                mark_complete=mark_complete,
                mark_incomplete=mark_incomplete,
                now_ts=time.time(),
            )
            return json_response(200, body, origin)
        return json_response(404, {"message": "Not found", "code": "not_found"}, origin)
    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={"action": action, "status_code": e.status_code, "error_code": e.code},
        )
        return _api_error_response(e, origin)
    except Exception:
        logger.exception("progress handler failed", extra={"action": action})
        return json_response(500, {"message": "Internal error", "code": "internal_error"}, origin)
