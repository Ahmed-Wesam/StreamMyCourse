"""Helpers for Kinescope HTTP routes that must be served by the video provider edge."""

from __future__ import annotations

from typing import Any, Dict

from config import AppConfig
from services.common.validation import parse_json_body


def _upload_kind_is_s3_thumbnail(upload_kind: str | None) -> bool:
    kind = (upload_kind or "lesson").strip() or "lesson"
    return kind in ("thumbnail", "lessonThumbnail")


def upload_kind_from_apigw_event(event: Dict[str, Any]) -> str | None:
    """Best-effort uploadKind for POST /upload-url; None when body is absent or not JSON."""
    try:
        body = parse_json_body(event)
    except Exception:
        return None
    return str(body.get("uploadKind") or "lesson").strip() or "lesson"


def kinescope_http_routed_on_catalog(
    cfg: AppConfig,
    *,
    method: str,
    parts: list[str],
    upload_kind: str | None = None,
) -> bool:
    """True when this request hit catalog but Kinescope outbound HTTP belongs on the edge Lambda."""
    if (cfg.video_provider or "").strip().lower() != "kinescope":
        return False
    m = (method or "").upper()
    if m in ("POST", "OPTIONS") and parts == ["upload-url"]:
        if m == "POST" and _upload_kind_is_s3_thumbnail(upload_kind):
            return False
        return True
    if (
        m in ("PUT", "OPTIONS")
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "lessons"
        and parts[4] == "video-ready"
    ):
        return True
    if m in ("POST", "OPTIONS") and parts == ["webhooks", "kinescope"]:
        return True
    return False
