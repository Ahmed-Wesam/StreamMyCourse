"""Integration test helpers for active video provider selection."""

from __future__ import annotations

import os


def integration_video_provider() -> str:
    return os.environ.get("INTEGRATION_VIDEO_PROVIDER", "kinescope").strip().lower()


def expects_s3_presigned_upload() -> bool:
    return integration_video_provider() == "s3"


def expects_kinescope() -> bool:
    return integration_video_provider() == "kinescope"


def integration_kinescope_webhook_secret() -> str:
    """Webhook secret for synthetic Kinescope POSTs (matches deployed stack when set)."""
    direct = os.environ.get("INTEGRATION_KINESCOPE_WEBHOOK_SECRET", "").strip()
    if direct:
        return direct
    return os.environ.get("KINESCOPE_WEBHOOK_SECRET", "").strip()
