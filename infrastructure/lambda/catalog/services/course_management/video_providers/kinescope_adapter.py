from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Sequence

from services.common.errors import ServiceUnavailable
from services.course_management.video_providers.port import (
    KinescopePlayback,
    VideoPlayback,
    VideoUploadInit,
)

_EDGE_REQUIRED_MSG = "Use video provider edge"

_DONE_API_STATUSES = frozenset({"done", "ready", "published", "active", "public"})
_FAILED_API_STATUSES = frozenset({"error", "failed", "aborted", "cancelled", "canceled"})


@dataclass(frozen=True)
class KinescopeVideoMetadata:
    status: str
    duration_seconds: int | None = None


def webhook_status_confirmed_by_api(webhook_status: str, api_status: str) -> bool:
    """True when Kinescope GET /videos/{id} status matches a mutating webhook event."""
    wh = (webhook_status or "").strip().lower()
    api = (api_status or "").strip().lower()
    if wh == "done":
        return api in _DONE_API_STATUSES
    if wh in ("error", "aborted"):
        return api in _FAILED_API_STATUSES or wh == api
    return True


class KinescopeVideoAdapter:
    """Playback-only Kinescope adapter for VPC catalog; outbound provider HTTP lives on edge."""

    def __init__(
        self,
        *,
        api_token: str = "",
        parent_id: str = "",
        default_filesize: int = 1,
    ) -> None:
        _ = api_token, parent_id, default_filesize

    @property
    def provider_id(self) -> Literal["kinescope"]:
        return "kinescope"

    @property
    def marks_ready_on_upload_complete(self) -> bool:
        return False

    def init_lesson_upload(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
        filesize: int | None = None,
    ) -> VideoUploadInit:
        _ = course_id, lesson_id, filename, content_type, expires_seconds, filesize
        raise ServiceUnavailable(_EDGE_REQUIRED_MSG)

    def resolve_playback(
        self,
        *,
        video_key: str,
        expires_seconds: int = 3600,
    ) -> VideoPlayback:
        _ = expires_seconds
        return KinescopePlayback(
            provider="kinescope",
            video_id=video_key,
            drm_auth_token="",
        )

    def delete_videos(self, keys: Sequence[str]) -> List[str]:
        if any((raw or "").strip() for raw in keys):
            raise ServiceUnavailable(_EDGE_REQUIRED_MSG)
        return []
