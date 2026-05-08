"""Lesson Progress Controller — HTTP request handling for progress endpoints.

This module implements:
- URL routing for progress endpoints
- Request parsing and validation
- Error mapping to JSON responses
- CORS header handling
"""

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
from services.common.validation import parse_json_body, require_int
from services.progress.contracts import (
    CourseProgressResponse,
    LessonProgressItem,
    UpdateProgressResponse,
)
from services.progress.service import LessonProgressService

logger = logging.getLogger(__name__)


def _extract_update_params(body: Dict[str, Any]) -> Tuple[int, int, bool, bool]:
    """Extract and validate update progress parameters from request body.

    Args:
        body: Parsed JSON request body

    Returns:
        Tuple of (position, duration, mark_complete, mark_incomplete)

    Raises:
        BadRequest: If validation fails
    """
    position = require_int(body, "position")
    if position < 0:
        raise BadRequest("position must be a non-negative integer")

    duration = require_int(body, "duration")
    if duration < 0:
        raise BadRequest("duration must be a non-negative integer")

    mark_complete = body.get("markComplete", False)
    mark_incomplete = body.get("markIncomplete", False)

    if mark_complete and mark_incomplete:
        raise BadRequest("Cannot specify both markComplete and markIncomplete")

    return position, duration, bool(mark_complete), bool(mark_incomplete)


def _api_error_payload(exc: HttpError) -> Dict[str, Any]:
    """Build error payload from HttpError."""
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return payload


def _api_error_response(exc: HttpError, origin: Optional[str]) -> Dict[str, Any]:
    """Build API error response with proper status code and headers."""
    return json_response(exc.status_code, _api_error_payload(exc), origin)


def _method_and_path(event: Dict[str, Any]) -> Tuple[str, str]:
    """Extract HTTP method and path from API Gateway event."""
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or ""
    )
    return method, apigw_routing_path(event)


def _actor_sub(claims: Dict[str, Any]) -> str:
    """Extract user sub from Cognito claims."""
    return str(claims.get("sub", "") or "").strip()


def _route(method: str, path: str) -> Tuple[str, Dict[str, str]]:
    """Route HTTP requests to actions.

    Args:
        method: HTTP method (GET, PUT, etc.)
        path: URL path

    Returns:
        Tuple of (action_name, path_parameters)
    """
    parts = [p for p in path.split("/") if p]

    # GET /courses/{id}/progress
    if method == "GET" and len(parts) == 3 and parts[0] == "courses" and parts[2] == "progress":
        return "get_course_progress", {"courseId": parts[1]}

    # PUT /courses/{id}/lessons/{id}/progress
    if method == "PUT" and len(parts) == 5 and parts[0] == "courses" and parts[2] == "lessons" and parts[4] == "progress":
        return "update_lesson_progress", {"courseId": parts[1], "lessonId": parts[3]}

    return "not_found", {}


def handle_progress_request(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    progress_svc: LessonProgressService,
) -> Dict[str, Any]:
    """Handle progress-related HTTP requests.

    Args:
        event: API Gateway Lambda event
        origin: CORS origin
        progress_svc: LessonProgressService instance

    Returns:
        API Gateway response dict
    """
    method, raw_path = _method_and_path(event)

    # Handle OPTIONS preflight
    if method == "OPTIONS":
        return options_response(origin)

    action, params = _route(method, raw_path)
    claims = apigw_cognito_claims(event)
    user_sub = _actor_sub(claims)

    try:
        if not user_sub:
            raise Unauthorized("Authentication required")
        if action == "get_course_progress":
            result: CourseProgressResponse = progress_svc.get_course_progress(
                user_sub=user_sub,
                course_id=params["courseId"],
            )
            return json_response(200, result, origin)

        if action == "update_lesson_progress":
            body = parse_json_body(event)
            position, duration, mark_complete, mark_incomplete = _extract_update_params(body)

            result: UpdateProgressResponse = progress_svc.update_lesson_progress(
                user_sub=user_sub,
                course_id=params["courseId"],
                lesson_id=params["lessonId"],
                position=position,
                duration=duration,
                mark_complete=mark_complete,
                mark_incomplete=mark_incomplete,
            )
            return json_response(200, result, origin)

        # Unknown route
        raise NotFound("Not found")

    except HttpError as e:
        # Log expected errors at INFO without stack trace
        logger.info(
            "HTTP error",
            extra={
                "action": action,
                "status_code": e.status_code,
                "error_code": e.code,
            },
        )
        return _api_error_response(e, origin)

    except Exception:
        logger.exception("Unhandled controller error", extra={"action": action})
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )
