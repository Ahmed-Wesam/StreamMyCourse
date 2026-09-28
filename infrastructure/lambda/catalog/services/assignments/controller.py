"""HTTP handlers for assignments (RS-13)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.assignments.service import AssignmentsService
from services.common.errors import HttpError, NotFound, Unauthorized
from services.common.http import (
    apigw_cognito_claims,
    apigw_routing_path,
    json_response,
    options_response,
)
from services.common.validation import parse_json_body

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

    # /courses/{courseId}/assignments
    if (
        method in ("GET", "POST")
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "assignments"
    ):
        action = "list_assignments" if method == "GET" else "create_assignment"
        return action, {"courseId": parts[1]}

    # /courses/{courseId}/assignments/{assignmentId}
    if (
        method in ("GET", "PATCH", "DELETE")
        and len(parts) == 4
        and parts[0] == "courses"
        and parts[2] == "assignments"
    ):
        action = {
            "GET": "get_assignment",
            "PATCH": "update_assignment",
            "DELETE": "delete_assignment",
        }[method]
        return action, {"courseId": parts[1], "assignmentId": parts[3]}

    # /courses/{courseId}/assignments/{assignmentId}/images
    if (
        method == "POST"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "images"
    ):
        return "create_image", {"courseId": parts[1], "assignmentId": parts[3]}

    # /courses/{courseId}/assignments/{assignmentId}/images/{slot}/complete
    if (
        method == "POST"
        and len(parts) == 7
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "images"
        and parts[6] == "complete"
    ):
        return "complete_image", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "slot": parts[5],
        }

    # /courses/{courseId}/assignments/{assignmentId}/images/{slot}/url
    if (
        method == "GET"
        and len(parts) == 7
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "images"
        and parts[6] == "url"
    ):
        return "get_image_url", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "slot": parts[5],
        }

    # /courses/{courseId}/assignments/{assignmentId}/submissions
    if (
        method in ("GET", "POST")
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "submissions"
    ):
        action = "list_submissions" if method == "GET" else "open_draft"
        return action, {"courseId": parts[1], "assignmentId": parts[3]}

    # /courses/{courseId}/assignments/{assignmentId}/submissions/{submissionId}/files
    if (
        method == "POST"
        and len(parts) == 7
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "submissions"
        and parts[6] == "files"
    ):
        return "create_file", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "submissionId": parts[5],
        }

    # .../submissions/{submissionId}/files/{fileId}/complete
    if (
        method == "POST"
        and len(parts) == 9
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "submissions"
        and parts[6] == "files"
        and parts[8] == "complete"
    ):
        return "complete_file", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "submissionId": parts[5],
            "fileId": parts[7],
        }

    # .../submissions/{submissionId}/files/{fileId}/url
    if (
        method == "GET"
        and len(parts) == 9
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "submissions"
        and parts[6] == "files"
        and parts[8] == "url"
    ):
        return "get_file_url", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "submissionId": parts[5],
            "fileId": parts[7],
        }

    # .../submissions/{submissionId}/submit
    if (
        method == "POST"
        and len(parts) == 7
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "submissions"
        and parts[6] == "submit"
    ):
        return "submit", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "submissionId": parts[5],
        }

    # .../submissions/{submissionId}/grade
    if (
        method == "POST"
        and len(parts) == 7
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "submissions"
        and parts[6] == "grade"
    ):
        return "grade", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "submissionId": parts[5],
        }

    # .../submissions/{submissionId}
    if (
        method == "GET"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "assignments"
        and parts[4] == "submissions"
    ):
        return "get_submission", {
            "courseId": parts[1],
            "assignmentId": parts[3],
            "submissionId": parts[5],
        }

    return "not_found", {}


def _api_error_payload(exc: HttpError) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"message": exc.message}
    if exc.code:
        payload["code"] = exc.code
    return payload


def handle_assignments_request(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    assignments_svc: AssignmentsService,
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

        if action == "list_assignments":
            result = assignments_svc.list_assignments(
                params["courseId"], cognito_sub=user_sub, role=role
            )
            return json_response(200, result, origin)

        if action == "create_assignment":
            body = parse_json_body(event)
            result = assignments_svc.create_assignment(
                params["courseId"],
                title=body.get("title"),
                module_id=body.get("moduleId"),
                pass_percent=body.get("passPercent"),
                counts_toward_certificate=body.get("countsTowardCertificate"),
                cognito_sub=user_sub,
                role=role,
                body=body,
            )
            return json_response(201, result, origin)

        if action == "get_assignment":
            result = assignments_svc.get_assignment(
                params["courseId"],
                params["assignmentId"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "update_assignment":
            body = parse_json_body(event)
            result = assignments_svc.update_assignment(
                params["courseId"],
                params["assignmentId"],
                cognito_sub=user_sub,
                role=role,
                body=body,
            )
            return json_response(200, result, origin)

        if action == "delete_assignment":
            result = assignments_svc.delete_assignment(
                params["courseId"],
                params["assignmentId"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "create_image":
            body = parse_json_body(event)
            result = assignments_svc.create_image_upload(
                params["courseId"],
                params["assignmentId"],
                slot=body.get("slot"),
                content_type=body.get("contentType"),
                byte_size=body.get("byteSize"),
                cognito_sub=user_sub,
                role=role,
                body=body,
            )
            return json_response(200, result, origin)

        if action == "complete_image":
            result = assignments_svc.complete_image_upload(
                params["courseId"],
                params["assignmentId"],
                params["slot"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "get_image_url":
            result = assignments_svc.get_image_url(
                params["courseId"],
                params["assignmentId"],
                params["slot"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "list_submissions":
            result = assignments_svc.list_submissions(
                params["courseId"],
                params["assignmentId"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "open_draft":
            body = parse_json_body(event) if event.get("body") else {}
            result = assignments_svc.open_draft_submission(
                params["courseId"],
                params["assignmentId"],
                cognito_sub=user_sub,
                role=role,
                body=body if isinstance(body, dict) else {},
            )
            return json_response(201, result, origin)

        if action == "create_file":
            body = parse_json_body(event)
            result = assignments_svc.create_submission_file(
                params["courseId"],
                params["assignmentId"],
                params["submissionId"],
                title=body.get("title"),
                file_type=body.get("fileType"),
                byte_size=body.get("byteSize"),
                cognito_sub=user_sub,
                role=role,
                body=body,
            )
            return json_response(200, result, origin)

        if action == "complete_file":
            result = assignments_svc.complete_submission_file(
                params["courseId"],
                params["assignmentId"],
                params["submissionId"],
                params["fileId"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "get_file_url":
            result = assignments_svc.get_submission_file_url(
                params["courseId"],
                params["assignmentId"],
                params["submissionId"],
                params["fileId"],
                cognito_sub=user_sub,
                role=role,
            )
            return json_response(200, result, origin)

        if action == "submit":
            body = parse_json_body(event) if event.get("body") else {}
            result = assignments_svc.submit_submission(
                params["courseId"],
                params["assignmentId"],
                params["submissionId"],
                note=body.get("note") if isinstance(body, dict) else None,
                cognito_sub=user_sub,
                role=role,
                body=body if isinstance(body, dict) else {},
            )
            return json_response(200, result, origin)

        if action == "grade":
            body = parse_json_body(event)
            result = assignments_svc.grade_submission(
                params["courseId"],
                params["assignmentId"],
                params["submissionId"],
                scores=body.get("scores") or [],
                feedback=body.get("feedback"),
                cognito_sub=user_sub,
                role=role,
                body=body,
            )
            return json_response(200, result, origin)

        if action == "get_submission":
            result = assignments_svc.get_submission(
                params["courseId"],
                params["assignmentId"],
                params["submissionId"],
                cognito_sub=user_sub,
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
