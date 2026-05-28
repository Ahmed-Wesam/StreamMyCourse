"""Kinescope HTTP client for video provider edge (non-VPC)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

_INIT_URL = "https://uploader.kinescope.io/v2/init"
_VIDEO_API_BASE = "https://api.kinescope.io/v1/videos"
_DEFAULT_FILESIZE = 1
TUS_FILESIZE_THRESHOLD_BYTES = 5 * 1024 * 1024 * 1024


@dataclass(frozen=True)
class KinescopeUploadInit:
    upload_url: str
    video_key: str
    upload_method: Literal["post", "tus"] = "post"


@dataclass(frozen=True)
class KinescopeVideoMetadata:
    status: str
    duration_seconds: int | None = None


class KinescopeUploadError(Exception):
    """Kinescope upload init failed."""


class KinescopeMetadataError(Exception):
    """Kinescope metadata fetch failed."""


_DONE_API_STATUSES = frozenset({"done", "ready", "published", "active", "public"})
_FAILED_API_STATUSES = frozenset({"error", "failed", "aborted", "cancelled", "canceled"})


def video_status_confirms_done(status: str) -> bool:
    return (status or "").strip().lower() in _DONE_API_STATUSES


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


def init_kinescope_lesson_upload(
    *,
    api_token: str,
    parent_id: str,
    filename: str,
    filesize: int | None = None,
    default_filesize: int = _DEFAULT_FILESIZE,
) -> KinescopeUploadInit:
    token = (api_token or "").strip()
    parent = (parent_id or "").strip()
    if not token or not parent:
        raise KinescopeUploadError("Video uploads are not configured")

    size = default_filesize if filesize is None else filesize
    if size <= 0:
        raise KinescopeUploadError("Invalid upload file size")

    payload = {
        "filesize": size,
        "type": "video",
        "title": _title_from_filename(filename),
        "parent_id": parent,
        "filename": filename,
    }
    req = Request(
        _INIT_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        logger.warning("Kinescope init upload HTTP error status=%s", exc.code)
        raise KinescopeUploadError("Failed to initiate video upload") from exc
    except URLError as exc:
        logger.warning("Kinescope init upload network error: %s", exc.reason)
        raise KinescopeUploadError("Failed to initiate video upload") from exc

    try:
        parsed = json.loads(raw)
        data = parsed["data"]
        video_id = str(data["id"]).strip()
        endpoint = str(data["endpoint"]).strip()
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.warning("Kinescope init upload returned unexpected JSON shape")
        raise KinescopeUploadError("Failed to initiate video upload") from exc

    upload_method: Literal["post", "tus"] = (
        "tus" if size >= TUS_FILESIZE_THRESHOLD_BYTES else "post"
    )
    return KinescopeUploadInit(
        upload_url=endpoint,
        video_key=video_id,
        upload_method=upload_method,
    )


def fetch_video_metadata(*, api_token: str, video_id: str) -> KinescopeVideoMetadata | None:
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


def delete_kinescope_video(*, api_token: str, video_id: str) -> bool:
    token = (api_token or "").strip()
    vid = (video_id or "").strip()
    if not token or not vid:
        logger.warning("Kinescope delete skipped: missing token or video_id")
        return False
    req = Request(
        f"{_VIDEO_API_BASE}/{vid}",
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
        logger.warning("Kinescope delete HTTP error video_id=%s status=%s", vid, exc.code)
        return False
    except URLError as exc:
        logger.warning("Kinescope delete network error video_id=%s: %s", vid, exc.reason)
        return False
