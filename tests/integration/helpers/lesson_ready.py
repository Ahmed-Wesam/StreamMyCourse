"""Helpers to mark lesson videos ready for integration fixtures."""

from __future__ import annotations

from helpers.api import ApiClient


def ensure_lesson_video_ready(
    api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    thumbnail_key: str | None = None,
) -> None:
    """Mark lesson video ready (S3 immediate; Kinescope sync-from-provider or dev bypass)."""
    resp = api.mark_video_ready(
        course_id,
        lesson_id,
        thumbnail_key=thumbnail_key,
    )
    assert resp.status_code == 200, (
        f"mark_video_ready failed: {resp.status_code} {resp.text}"
    )
