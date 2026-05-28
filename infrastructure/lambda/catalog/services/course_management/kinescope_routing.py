"""Helpers for Kinescope HTTP routes that must be served by the video provider edge."""

from __future__ import annotations

from config import AppConfig


def kinescope_http_routed_on_catalog(cfg: AppConfig, *, method: str, parts: list[str]) -> bool:
    """True when this request hit catalog but Kinescope outbound HTTP belongs on the edge Lambda."""
    if (cfg.video_provider or "").strip().lower() != "kinescope":
        return False
    m = (method or "").upper()
    if m in ("POST", "OPTIONS") and parts == ["upload-url"]:
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
