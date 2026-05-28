"""Kinescope DRM auth webhook — subscription/owner access via Kinescope payload shape."""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription
from helpers.kinescope_drm_auth import post_kinescope_drm_auth
from helpers.playback_contract import assert_playback_contract
from helpers.video_provider import expects_kinescope

pytestmark = pytest.mark.skipif(
    not expects_kinescope(),
    reason="DRM auth integration tests require INTEGRATION_VIDEO_PROVIDER=kinescope",
)


def _publish_ready_lesson(
    api: ApiClient,
    course_factory,
    lesson_factory,
    *,
    label: str,
) -> tuple[str, str]:
    course = course_factory(label=label)
    course_id = course.course_id
    lesson = lesson_factory(course_id, label=f"{label}-lesson")
    lesson_id = lesson.lesson_id

    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, ready_resp.text

    publish_resp = api.publish_course(course_id)
    assert publish_resp.status_code == 200, publish_resp.text
    return course_id, lesson_id


def test_drm_auth_allows_subscribed_student_kinescope_payload(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    course_id, lesson_id = _publish_ready_lesson(
        api, course_factory, lesson_factory, label="drm-auth-subscribed"
    )
    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

    playback_resp = student_api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, playback_resp.text
    playback = playback_resp.json()
    assert_playback_contract(playback)
    if playback.get("provider") != "kinescope":
        pytest.skip("playback provider is not kinescope on this stack")

    drm_resp = post_kinescope_drm_auth(
        student_api,
        video_id=playback["videoId"],
        token=playback["drmAuthToken"],
    )
    assert drm_resp.status_code == 200, drm_resp.text
    assert drm_resp.json().get("allow") is True

    api.delete_course(course_id)


def test_drm_auth_denies_mismatched_video_id(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    course_id, lesson_id = _publish_ready_lesson(
        api, course_factory, lesson_factory, label="drm-auth-mismatch"
    )
    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

    playback_resp = student_api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, playback_resp.text
    playback = playback_resp.json()
    if playback.get("provider") != "kinescope":
        pytest.skip("playback provider is not kinescope on this stack")

    drm_resp = post_kinescope_drm_auth(
        student_api,
        video_id="00000000-0000-4000-8000-000000000000",
        token=playback["drmAuthToken"],
    )
    assert drm_resp.status_code == 403, drm_resp.text
    assert drm_resp.json().get("allow") is False

    api.delete_course(course_id)


def test_drm_auth_allows_course_owner_without_subscription(
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    course_id, lesson_id = _publish_ready_lesson(
        api, course_factory, lesson_factory, label="drm-auth-owner"
    )

    playback_resp = api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, playback_resp.text
    playback = playback_resp.json()
    if playback.get("provider") != "kinescope":
        pytest.skip("playback provider is not kinescope on this stack")

    drm_resp = post_kinescope_drm_auth(
        api,
        video_id=playback["videoId"],
        token=playback["drmAuthToken"],
    )
    assert drm_resp.status_code == 200, drm_resp.text
    assert drm_resp.json().get("allow") is True

    api.delete_course(course_id)


def test_drm_auth_denies_invalid_token(api: ApiClient) -> None:
    drm_resp = post_kinescope_drm_auth(
        api,
        video_id="00000000-0000-4000-8000-000000000001",
        token="not.a.valid.jwt",
    )
    assert drm_resp.status_code == 403, drm_resp.text
    assert drm_resp.json().get("allow") is False
