"""Integration tests for Kinescope media.update.status webhook handling."""

from __future__ import annotations

import uuid

import pytest

from helpers.api import ApiClient
from helpers.kinescope_webhook import post_kinescope_media_status
from helpers.video_provider import expects_kinescope

pytestmark = pytest.mark.skipif(
    not expects_kinescope(),
    reason="Kinescope webhook tests require INTEGRATION_VIDEO_PROVIDER=kinescope",
)


def test_kinescope_webhook_unknown_video_id_is_ignored(api: ApiClient) -> None:
    resp = post_kinescope_media_status(
        api,
        video_id=str(uuid.uuid4()),
        status="done",
    )
    assert resp.status_code == 200
    assert resp.json().get("ignored") is True


def test_kinescope_webhook_spoofed_done_not_applied_without_kinescope_ready(
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Forged done events must not flip lesson ready unless Kinescope API confirms done."""
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    upload = api.get_upload_url(
        course_id=course.course_id,
        lesson_id=lesson.lesson_id,
        filesize=1024,
    )
    assert upload.status_code == 200
    video_id = upload.json()["videoKey"]

    webhook = post_kinescope_media_status(api, video_id=video_id, status="done")
    assert webhook.status_code == 200
    body = webhook.json()
    assert body.get("ignored") is True or body.get("videoStatus") != "ready"

    listing = api.list_lessons(course.course_id)
    assert listing.status_code == 200
    item = next(row for row in listing.json() if row["id"] == lesson.lesson_id)
    assert item["videoStatus"] == "pending"


def test_kinescope_webhook_rejects_missing_secret_when_configured(
    api: ApiClient,
) -> None:
    resp = post_kinescope_media_status(
        api,
        video_id=str(uuid.uuid4()),
        status="done",
        webhook_secret="",
    )
    assert resp.status_code == 401

    authed = post_kinescope_media_status(
        api,
        video_id=str(uuid.uuid4()),
        status="done",
    )
    assert authed.status_code == 200
