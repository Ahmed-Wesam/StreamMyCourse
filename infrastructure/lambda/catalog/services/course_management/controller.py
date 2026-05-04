from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

from services.common.errors import Forbidden, HttpError, NotFound, Unauthorized
from services.common.http import apigw_cognito_claims, apigw_routing_path, json_response, options_response
from services.common.runtime_context import update_action
from services.common.validation import optional_str, parse_json_body, require_str
from services.course_management import contracts as dto
from services.course_management.ports import UserProfileProvisioner
from services.course_management.service import CourseManagementService

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


def _jwt_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    return apigw_cognito_claims(event)


def _actor_sub(claims: Dict[str, Any]) -> str:
    return str(claims.get("sub", "") or "").strip()


def _actor_role(claims: Dict[str, Any]) -> str:
    return str(claims.get("custom:role") or claims.get("role") or "student").strip().lower()


def _audit_event(action: str, course_id: str, claims: Dict[str, Any]) -> None:
    sub = _actor_sub(claims)
    prefix = sub[:8] if sub else ""
    logger.info(
        "audit_event",
        extra={
            "audit_action": action,
            "course_id": course_id,
            "user_sub_prefix": prefix,
        },
    )


def _require_authenticated(auth_enforced: bool, claims: Dict[str, Any]) -> None:
    if not auth_enforced:
        return
    if not _actor_sub(claims):
        raise Unauthorized("Authentication required")


def _require_teacher_or_admin(auth_enforced: bool, claims: Dict[str, Any]) -> None:
    _require_authenticated(auth_enforced, claims)
    if not auth_enforced:
        return
    if _actor_role(claims) not in ("teacher", "admin"):
        raise Forbidden("Teacher or admin role required")


def _route(method: str, path: str) -> Tuple[str, Dict[str, str]]:
    parts = [p for p in path.split("/") if p]
    if method == "GET" and parts == ["courses"]:
        return "list_courses", {}
    if method == "POST" and parts == ["courses"]:
        return "create_course", {}
    if method == "GET" and len(parts) == 3 and parts[0] == "courses" and parts[2] == "preview":
        return "get_course_preview", {"courseId": parts[1]}
    if method == "POST" and len(parts) == 3 and parts[0] == "courses" and parts[2] == "enroll":
        return "enroll_course", {"courseId": parts[1]}
    if method == "GET" and len(parts) == 2 and parts[0] == "courses" and parts[1] == "mine":
        return "list_instructor_courses", {}
    if method == "GET" and len(parts) == 2 and parts[0] == "courses":
        return "get_course", {"courseId": parts[1]}
    if method == "PUT" and len(parts) == 2 and parts[0] == "courses":
        return "update_course", {"courseId": parts[1]}
    if method == "PUT" and len(parts) == 3 and parts[0] == "courses" and parts[2] == "thumbnail-ready":
        return "mark_thumbnail_ready", {"courseId": parts[1]}
    if method == "PUT" and len(parts) == 3 and parts[0] == "courses" and parts[2] == "publish":
        return "publish_course", {"courseId": parts[1]}
    if method == "DELETE" and len(parts) == 2 and parts[0] == "courses":
        return "delete_course", {"courseId": parts[1]}
    if method == "GET" and len(parts) == 3 and parts[0] == "courses" and parts[2] == "lessons":
        return "list_lessons", {"courseId": parts[1]}
    if method == "POST" and len(parts) == 3 and parts[0] == "courses" and parts[2] == "lessons":
        return "create_lesson", {"courseId": parts[1]}
    if method == "PUT" and len(parts) == 4 and parts[0] == "courses" and parts[2] == "lessons":
        return "update_lesson", {"courseId": parts[1], "lessonId": parts[3]}
    if method == "DELETE" and len(parts) == 4 and parts[0] == "courses" and parts[2] == "lessons":
        return "delete_lesson", {"courseId": parts[1], "lessonId": parts[3]}
    if (
        method == "PUT"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "lessons"
        and parts[4] == "video-ready"
    ):
        return "mark_video_ready", {"courseId": parts[1], "lessonId": parts[3]}
    if method == "GET" and len(parts) == 3 and parts[0] == "playback":
        return "get_playback", {"courseId": parts[1], "lessonId": parts[2]}
    if method == "POST" and parts == ["upload-url"]:
        return "get_upload_url", {}
    return "not_found", {}


def handle(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    svc: CourseManagementService,
    video_bucket: str,
    auth_svc: UserProfileProvisioner,
    auth_enforced: bool = False,
) -> Dict[str, Any]:
    method, raw_path = _method_and_path(event)
    if method == "OPTIONS":
        return options_response(origin)

    action, params = _route(method, raw_path)
    # Set action in context for correlation logging
    update_action(action)
    claims = _jwt_claims(event)

    try:
        if action == "list_courses":
            return json_response(200, dto.as_course_list(svc.list_published_courses()), origin)
        if action == "create_course":
            _require_teacher_or_admin(auth_enforced, claims)
            body = parse_json_body(event)
            title = optional_str(body, "title", "Untitled Course")
            description = optional_str(body, "description", "")
            created: dto.CreateCourseResponse = svc.create_course(
                title,
                description,
                created_by=_actor_sub(claims) if auth_enforced else "",
            )  # type: ignore[assignment]
            return json_response(201, created, origin)
        if action == "get_course_preview":
            preview_body = svc.get_course_preview(params["courseId"])
            return json_response(200, preview_body, origin)
        if action == "enroll_course":
            _require_authenticated(auth_enforced, claims)
            sub = _actor_sub(claims)
            email = str(claims.get("email", "") or "").strip()
            role = str(claims.get("custom:role") or claims.get("role") or "student").strip()
            try:
                auth_svc.get_or_create_profile(user_sub=sub, email=email, role=role)
            except HttpError as e:
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
                logger.exception("enroll profile upsert failed", extra={"action": action})
                return json_response(
                    500, {"message": "Internal error", "code": "internal_error"}, origin
                )
            enrolled_body = svc.enroll_in_published_course(
                params["courseId"],
                cognito_sub=sub,
            )
            _audit_event("enrollment.create", params["courseId"], claims)
            return json_response(200, enrolled_body, origin)
        if action == "list_instructor_courses":
            _require_teacher_or_admin(auth_enforced, claims)
            mine = svc.list_instructor_courses(
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            return json_response(200, dto.as_course_list(mine), origin)
        if action == "get_course":
            _require_authenticated(auth_enforced, claims)
            detail = svc.get_course_detail_with_enrollment(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            return json_response(200, dto.as_course_dto(detail), origin)
        if action == "update_course":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            body = parse_json_body(event)
            title = optional_str(body, "title", "")
            description = optional_str(body, "description", "")
            updated: dto.UpdateCourseResponse = svc.update_course(params["courseId"], title, description)  # type: ignore[assignment]
            return json_response(200, updated, origin)
        if action == "publish_course":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            published: dto.PublishCourseResponse = svc.publish_course(params["courseId"])  # type: ignore[assignment]
            return json_response(200, published, origin)
        if action == "delete_course":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            deleted: dto.DeleteCourseResponse = svc.delete_course(params["courseId"])  # type: ignore[assignment]
            _audit_event("course.delete", params["courseId"], claims)
            return json_response(200, deleted, origin)
        if action == "list_lessons":
            _require_authenticated(auth_enforced, claims)
            svc.ensure_can_view_lessons_and_playback(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            return json_response(200, dto.as_lesson_list(svc.list_lessons(params["courseId"])), origin)
        if action == "create_lesson":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            body = parse_json_body(event)
            title = optional_str(body, "title", "Lesson")
            created_lesson: dto.CreateLessonResponse = svc.create_lesson(params["courseId"], title)  # type: ignore[assignment]
            return json_response(201, created_lesson, origin)
        if action == "update_lesson":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            body = parse_json_body(event)
            title = optional_str(body, "title", "")
            updated_lesson: dto.UpdateLessonResponse = svc.update_lesson(params["courseId"], params["lessonId"], title)  # type: ignore[assignment]
            return json_response(200, updated_lesson, origin)
        if action == "delete_lesson":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            deleted_lesson: dto.DeleteLessonResponse = svc.delete_lesson(params["courseId"], params["lessonId"])  # type: ignore[assignment]
            return json_response(200, deleted_lesson, origin)
        if action == "mark_video_ready":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            body = parse_json_body(event)
            thumb_for_lesson = optional_str(body, "thumbnailKey", "") or ""
            ready: dto.MarkVideoReadyResponse = svc.mark_lesson_video_ready(  # type: ignore[assignment]
                params["courseId"],
                params["lessonId"],
                thumbnail_key=thumb_for_lesson.strip() or None,
            )
            return json_response(200, ready, origin)
        if action == "mark_thumbnail_ready":
            svc.ensure_can_modify_course(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            body = parse_json_body(event)
            thumbnail_key = require_str(body, "thumbnailKey")
            thumb: dto.MarkThumbnailReadyResponse = svc.mark_course_thumbnail_ready(  # type: ignore[assignment]
                params["courseId"], thumbnail_key
            )
            return json_response(200, thumb, origin)
        if action == "get_playback":
            _require_authenticated(auth_enforced, claims)
            svc.ensure_can_view_lessons_and_playback(
                params["courseId"],
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            playback: dto.PlaybackResponse = svc.get_playback_url(  # type: ignore[assignment]
                params["courseId"], params["lessonId"], video_bucket=video_bucket
            )
            return json_response(200, playback, origin)
        if action == "get_upload_url":
            body = parse_json_body(event)
            course_id = require_str(body, "courseId")
            svc.ensure_can_modify_course(
                course_id,
                cognito_sub=_actor_sub(claims),
                role=_actor_role(claims),
                auth_enforced=auth_enforced,
            )
            filename = optional_str(body, "filename", "video.mp4")
            content_type = optional_str(body, "contentType", "video/mp4") or "video/mp4"
            upload_kind = optional_str(body, "uploadKind", "lesson") or "lesson"
            if upload_kind == "thumbnail":
                thumb_upload: dto.UploadUrlResponse = svc.get_thumbnail_upload_url(  # type: ignore[assignment]
                    course_id=course_id, filename=filename, content_type=content_type
                )
                return json_response(200, thumb_upload, origin)
            if upload_kind == "lessonThumbnail":
                lesson_thumb_id = require_str(body, "lessonId")
                lesson_thumb: dto.UploadUrlResponse = svc.get_lesson_thumbnail_upload_url(  # type: ignore[assignment]
                    course_id=course_id,
                    lesson_id=lesson_thumb_id,
                    filename=filename,
                    content_type=content_type,
                )
                return json_response(200, lesson_thumb, origin)
            lesson_id = require_str(body, "lessonId")
            upload: dto.UploadUrlResponse = svc.get_upload_url(  # type: ignore[assignment]
                course_id=course_id, lesson_id=lesson_id, filename=filename, content_type=content_type
            )
            return json_response(200, upload, origin)

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
        return json_response(500, {"message": "Internal error", "code": "internal_error"}, origin)

