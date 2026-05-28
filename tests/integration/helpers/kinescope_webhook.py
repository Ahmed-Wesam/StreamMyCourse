"""Synthetic Kinescope webhook POST helper for integration tests."""

from __future__ import annotations

from typing import Any

import httpx

from helpers.api import ApiClient
from helpers.video_provider import integration_kinescope_webhook_secret


def post_kinescope_media_status(
    api: ApiClient,
    *,
    video_id: str,
    status: str,
    message: str = "",
    webhook_secret: str | None = None,
) -> httpx.Response:
    payload: dict[str, Any] = {
        "event": "media.update.status",
        "data": {"id": video_id, "status": status},
    }
    if message:
        payload["data"]["message"] = message

    secret = (
        integration_kinescope_webhook_secret()
        if webhook_secret is None
        else webhook_secret
    )

    headers: dict[str, str] = {}
    if secret:
        headers["X-Kinescope-Webhook-Secret"] = secret

    path = "/webhooks/kinescope"
    if secret:
        path = f"{path}?token={secret}"

    return api.raw.post(path, json=payload, headers=headers)
