"""Direct Lambda invoke handlers for video provider edge orchestration."""

from __future__ import annotations

from typing import Any, Dict

from services.common.errors import Conflict
from services.course_management.service import CourseManagementService
from services.course_management.video_providers.kinescope_adapter import KinescopeVideoMetadata


def _user_sub_from_event(event: Dict[str, Any]) -> str:
    return str(event.get("userSub") or event.get("user_sub") or "").strip()


def _role_from_event(event: Dict[str, Any]) -> str:
    return str(event.get("role") or "student").strip().lower() or "student"


def _provider_metadata_from_event(event: Dict[str, Any]) -> KinescopeVideoMetadata | None:
    raw = event.get("providerMetadata")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("providerMetadata must be an object when present")
    status = str(raw.get("status") or "").strip().lower()
    if not status:
        return None
    duration_raw = raw.get("durationSeconds")
    duration_seconds: int | None = None
    if duration_raw is not None:
        duration_seconds = int(duration_raw)
    return KinescopeVideoMetadata(status=status, duration_seconds=duration_seconds)


def handle_internal_video_prepare_upload(
    event: Dict[str, Any],
    *,
    course_service: CourseManagementService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for video.prepare_upload")

    course_id = str(event.get("courseId") or "").strip()
    lesson_id = str(event.get("lessonId") or "").strip()
    if not course_id or not lesson_id:
        raise ValueError("courseId and lessonId are required for video.prepare_upload")

    filename = str(event.get("filename") or "video.mp4").strip() or "video.mp4"
    content_type = str(event.get("contentType") or "video/mp4").strip() or "video/mp4"
    filesize_raw = event.get("filesize")
    filesize: int | None = None
    if filesize_raw is not None:
        filesize = int(filesize_raw)

    return course_service.prepare_lesson_video_upload(
        course_id=course_id,
        lesson_id=lesson_id,
        filename=filename,
        content_type=content_type,
        filesize=filesize,
        cognito_sub=user_sub,
        role=_role_from_event(event),
    )


def handle_internal_video_commit_pending_upload(
    event: Dict[str, Any],
    *,
    course_service: CourseManagementService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for video.commit_pending_upload")

    course_id = str(event.get("courseId") or "").strip()
    lesson_id = str(event.get("lessonId") or "").strip()
    video_key = str(event.get("videoKey") or "").strip()
    if not course_id or not lesson_id or not video_key:
        raise ValueError(
            "courseId, lessonId, and videoKey are required for video.commit_pending_upload"
        )

    expected_video_key = str(event.get("expectedVideoKey") or "").strip()

    try:
        return course_service.commit_pending_lesson_video_upload(
            course_id=course_id,
            lesson_id=lesson_id,
            video_key=video_key,
            expected_video_key=expected_video_key,
            cognito_sub=user_sub,
            role=_role_from_event(event),
        )
    except Conflict as exc:
        return {"errorCode": "upload_conflict", "message": str(exc)}


def handle_internal_video_prepare_mark_ready(
    event: Dict[str, Any],
    *,
    course_service: CourseManagementService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for video.prepare_mark_ready")

    course_id = str(event.get("courseId") or "").strip()
    lesson_id = str(event.get("lessonId") or "").strip()
    if not course_id or not lesson_id:
        raise ValueError("courseId and lessonId are required for video.prepare_mark_ready")

    return course_service.prepare_lesson_video_mark_ready(
        course_id=course_id,
        lesson_id=lesson_id,
        cognito_sub=user_sub,
        role=_role_from_event(event),
    )


def handle_internal_video_apply_mark_ready(
    event: Dict[str, Any],
    *,
    course_service: CourseManagementService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for video.apply_mark_ready")

    course_id = str(event.get("courseId") or "").strip()
    lesson_id = str(event.get("lessonId") or "").strip()
    video_key = str(event.get("videoKey") or "").strip()
    if not course_id or not lesson_id or not video_key:
        raise ValueError(
            "courseId, lessonId, and videoKey are required for video.apply_mark_ready"
        )

    thumbnail_key = str(event.get("thumbnailKey") or "").strip() or None
    provider_metadata_supplied = bool(event.get("providerMetadataSupplied"))
    provider_metadata = _provider_metadata_from_event(event) if provider_metadata_supplied else None

    return course_service.apply_lesson_video_mark_ready(
        course_id=course_id,
        lesson_id=lesson_id,
        video_key=video_key,
        cognito_sub=user_sub,
        role=_role_from_event(event),
        thumbnail_key=thumbnail_key,
        provider_metadata=provider_metadata,
        provider_metadata_supplied=provider_metadata_supplied,
    )


def handle_internal_video_webhook_status(
    event: Dict[str, Any],
    *,
    course_service: CourseManagementService,
) -> Dict[str, Any]:
    raw_payload = event.get("webhookPayload")
    if not isinstance(raw_payload, dict):
        raise ValueError("webhookPayload is required for video.webhook_status")

    provider_metadata_supplied = bool(event.get("providerMetadataSupplied"))
    verified_metadata = (
        _provider_metadata_from_event(event) if provider_metadata_supplied else None
    )

    return course_service.handle_kinescope_media_status(
        raw_payload,
        verified_metadata=verified_metadata,
        verified_metadata_supplied=provider_metadata_supplied,
    )
