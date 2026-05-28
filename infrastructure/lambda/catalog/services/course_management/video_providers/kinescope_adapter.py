from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List, Literal, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.common.errors import BadRequest, ServiceUnavailable
from services.course_management.video_providers.port import (
    KinescopePlayback,
    VideoPlayback,
    VideoUploadInit,
)

_INIT_URL = "https://uploader.kinescope.io/v2/init"
_VIDEO_API_BASE = "https://api.kinescope.io/v1/videos"
_DEFAULT_FILESIZE = 1
TUS_FILESIZE_THRESHOLD_BYTES = 5 * 1024 * 1024 * 1024

logger = logging.getLogger(__name__)

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


def _title_from_filename(filename: str) -> str:
    name = (filename or "").strip()
    if not name:
        return "Lesson video"
    if "." in name:
        return name.rsplit(".", 1)[0] or name
    return name


class KinescopeVideoAdapter:
    """Kinescope upload init via uploader.kinescope.io; playback/delete via REST API."""

    def __init__(
        self,
        *,
        api_token: str = "",
        parent_id: str = "",
        default_filesize: int = _DEFAULT_FILESIZE,
    ) -> None:
        self._api_token = (api_token or "").strip()
        self._parent_id = (parent_id or "").strip()
        self._default_filesize = default_filesize

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
        _ = course_id, lesson_id, content_type, expires_seconds
        if not self._api_token or not self._parent_id:
            raise BadRequest("Video uploads are not configured")

        size = self._default_filesize if filesize is None else filesize
        if size <= 0:
            raise BadRequest("Invalid upload file size")

        payload = {
            "filesize": size,
            "type": "video",
            "title": _title_from_filename(filename),
            "parent_id": self._parent_id,
            "filename": filename,
        }
        req = Request(
            _INIT_URL,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
        except HTTPError as exc:
            logger.warning("Kinescope init upload HTTP error status=%s", exc.code)
            raise ServiceUnavailable("Failed to initiate video upload") from exc
        except URLError as exc:
            logger.warning("Kinescope init upload network error: %s", exc.reason)
            raise ServiceUnavailable("Failed to initiate video upload") from exc

        try:
            parsed = json.loads(raw)
            data = parsed["data"]
            video_id = str(data["id"]).strip()
            endpoint = str(data["endpoint"]).strip()
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Kinescope init upload returned unexpected JSON shape")
            raise ServiceUnavailable("Failed to initiate video upload") from exc

        upload_method = "tus" if size >= TUS_FILESIZE_THRESHOLD_BYTES else "post"
        return VideoUploadInit(
            upload_url=endpoint,
            video_key=video_id,
            upload_method=upload_method,
        )

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
        deleted: List[str] = []
        for raw in keys:
            video_id = (raw or "").strip()
            if not video_id:
                continue
            if _delete_kinescope_video(api_token=self._api_token, video_id=video_id):
                deleted.append(video_id)
        return deleted


def _delete_kinescope_video(*, api_token: str, video_id: str) -> bool:
    token = (api_token or "").strip()
    if not token:
        logger.warning("Kinescope delete skipped: missing API token video_id=%s", video_id)
        return False
    req = Request(
        f"{_VIDEO_API_BASE}/{video_id}",
        method="DELETE",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            _ = resp.read()
        return True
    except HTTPError as exc:
        if exc.code == 404:
            return True
        logger.warning("Kinescope delete HTTP error video_id=%s status=%s", video_id, exc.code)
        return False
    except URLError as exc:
        logger.warning("Kinescope delete network error video_id=%s: %s", video_id, exc.reason)
        return False


def fetch_kinescope_video_metadata(*, api_token: str, video_id: str) -> KinescopeVideoMetadata | None:
    """Return status + floored duration from Kinescope GET /v1/videos/{id}, or None."""
    token = (api_token or "").strip()
    vid = (video_id or "").strip()
    if not token or not vid:
        return None
    req = Request(
        f"{_VIDEO_API_BASE}/{vid}",
        method="GET",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        logger.warning("Kinescope fetch metadata failed video_id=%s: %s", vid, exc)
        return None

    try:
        parsed = json.loads(raw)
        data = parsed["data"]
        status = str(data.get("status") or "").strip().lower()
        duration_raw = data.get("duration")
        duration_seconds: int | None = None
        if duration_raw is not None:
            duration = float(duration_raw)
            if duration > 0:
                duration_seconds = int(duration)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        logger.warning("Kinescope fetch metadata returned unexpected JSON for video_id=%s", vid)
        return None

    if not status:
        return None
    return KinescopeVideoMetadata(status=status, duration_seconds=duration_seconds)


def fetch_video_duration_seconds(*, api_token: str, video_id: str) -> int | None:
    """Return floored duration in seconds from Kinescope GET /v1/videos/{id}, or None."""
    metadata = fetch_kinescope_video_metadata(api_token=api_token, video_id=video_id)
    if metadata is None:
        return None
    return metadata.duration_seconds
