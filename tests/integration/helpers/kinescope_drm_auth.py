"""Synthetic Kinescope DRM auth callback POST helper for integration tests."""

from __future__ import annotations

from typing import Any

import httpx

from helpers.api import ApiClient


def post_kinescope_drm_auth(
    api: ApiClient,
    *,
    video_id: str,
    token: str,
) -> httpx.Response:
    """POST the payload shape Kinescope sends to the auth backend (`id` + `token`)."""
    payload: dict[str, Any] = {"id": video_id, "token": token}
    return api.raw.post("/webhooks/kinescope/drm-auth", json=payload)
