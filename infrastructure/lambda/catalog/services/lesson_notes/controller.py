"""HTTP handlers for lesson notes (routing only; wired in bootstrap later)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.common.errors import BadRequest, HttpError, NotFound, Unauthorized
from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
)
from services.common.validation import parse_json_body
from services.lesson_notes.service import LessonNotesService

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

    # GET|POST /courses/{courseId}/lessons/{lessonId}/notes
    if (
        method in ("GET", "POST")
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "lessons"
        and parts[4] == "notes"
    ):
        action = "list_notes" if method == "GET" else "create_note"
        return action, {"courseId": parts[1], "lessonId": parts[3]}

    # PATCH|DELETE /courses/{courseId}/lessons/{lessonId}/notes/{noteId}
    if (
        method in ("PATCH", "DELETE")
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "lessons"
        and parts[4] == "notes"
    ):
        action = "update_note" if method == "PATCH" else "delete_note"
        return action, {
            "courseId": parts[1],
            "lessonId": parts[3],
            "noteId": parts[5],
        }

    return "not_found", {}


def _parse_create_body(body: Dict[str, Any]) -> Tuple[str, int | None]:
    raw_body = body.get("body")
    if not isinstance(raw_body, str):
        raise BadRequest("'body' is required")
    ts: int | None = None
    if "timestampSec" in body and body["timestampSec"] is not None:
        val = body["timestampSec"]
        if isinstance(val, bool) or not isinstance(val, int):
            raise BadRequest("timestampSec must be an integer")
        ts = val
    return raw_body, ts


def _parse_update_body(body: Dict[str, Any]) -> Tuple[str | None, int | None, bool]:
    note_body: str | None = None
    if "body" in body:
        val = body["body"]
        if not isinstance(val, str):
            raise BadRequest("body must be a string")
        note_body = val
    ts: int | None = None
    clear_ts = False
    if "timestampSec" in body:
        val = body["timestampSec"]
        if val is None:
            clear_ts = True
        else:
            if isinstance(val, bool) or not isinstance(val, int):
                raise BadRequest("timestampSec must be an integer")
            ts = val
    return note_body, ts, clear_ts


def _api_error_payload(exc: HttpError) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return payload


def handle_lesson_notes_request(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    notes_svc: LessonNotesService,
) -> Dict[str, Any]:
    method, raw_path = _method_and_path(event)

    if method == "OPTIONS":
        return options_response(origin)

    action, params = _route(method, raw_path)
    claims = apigw_cognito_claims(event)
    user_sub = _actor_sub(claims)
    role = _actor_role(claims)

    try:
        if not user_sub:
            raise Unauthorized("Authentication required")

        if action == "list_notes":
            result = notes_svc.list_notes(
                user_sub,
                params["courseId"],
                params["lessonId"],
                role=role,
            )
            return json_response(200, result, origin)

        if action == "create_note":
            body = parse_json_body(event)
            note_body, ts = _parse_create_body(body)
            result = notes_svc.create_note(
                user_sub,
                params["courseId"],
                params["lessonId"],
                body=note_body,
                timestamp_sec=ts,
                role=role,
            )
            return json_response(201, result, origin)

        if action == "update_note":
            body = parse_json_body(event)
            note_body, ts, clear_ts = _parse_update_body(body)
            result = notes_svc.update_note(
                user_sub,
                params["courseId"],
                params["lessonId"],
                params["noteId"],
                body=note_body,
                timestamp_sec=ts,
                clear_timestamp=clear_ts,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "delete_note":
            result = notes_svc.delete_note(
                user_sub,
                params["courseId"],
                params["lessonId"],
                params["noteId"],
                role=role,
            )
            return json_response(200, result, origin)

        raise NotFound("Not found")

    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={
                "action": action,
                "status_code": e.status_code,
                "error_code": e.code,
            },
        )
        return json_response(e.status_code, _api_error_payload(e), origin)

    except Exception:
        logger.exception("Unhandled controller error", extra={"action": action})
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )
