"""Playback authorization tests — subscription-based content access.

These tests verify that playback URLs are only accessible to:
- Subscribed students (platform subscription)
- Course owners (teachers who created the course)
- Admins

Non-subscribed users should receive 403 Forbidden with subscription_required.
DRAFT course lessons should return 404 even with valid JWT.
"""

from __future__ import annotations

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription, skip_if_student_has_subscription


def test_subscribed_student_gets_playback_url(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Subscribed student should get 200 + presigned URL for playback."""
    course = course_factory(label="subscribed-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="subscribed-playback-lesson")
    lesson_id = lesson.lesson_id

    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

    playback_resp = student_api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, (
        f"Expected 200, got {playback_resp.status_code}: {playback_resp.text}"
    )
    body = playback_resp.json()
    assert "url" in body, f"Expected 'url' in response body: {body}"
    assert isinstance(body["url"], str), f"Expected url to be a string: {body}"
    assert len(body["url"]) > 0, "Expected non-empty presigned URL"

    api.delete_course(course_id)


def test_non_subscribed_user_gets_403(
    api: ApiClient,
    alt_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Non-subscribed user (alt teacher) should get 403 when trying to access playback."""
    course = course_factory(label="non-subscribed-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="non-subscribed-playback-lesson")
    lesson_id = lesson.lesson_id

    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    playback_resp = alt_api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 403, (
        f"Expected 403, got {playback_resp.status_code}: {playback_resp.text}"
    )
    body = playback_resp.json()
    assert body.get("code") in ["forbidden", "subscription_required"], (
        f"Expected code 'forbidden' or 'subscription_required', got {body.get('code')}"
    )

    api.delete_course(course_id)


def test_course_owner_gets_playback_url(
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Course owner should get 200 + presigned URL even without formal subscription."""
    course = course_factory(label="owner-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="owner-playback-lesson")
    lesson_id = lesson.lesson_id

    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    playback_resp = api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, (
        f"Expected 200, got {playback_resp.status_code}: {playback_resp.text}"
    )
    body = playback_resp.json()
    assert "url" in body, f"Expected 'url' in response body: {body}"
    assert isinstance(body["url"], str), f"Expected url to be a string: {body}"
    assert len(body["url"]) > 0, "Expected non-empty presigned URL"

    api.delete_course(course_id)


def test_draft_lesson_playback_returns_404(
    api: ApiClient,
    alt_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Non-subscribed user should get 403/404 for DRAFT course lesson playback.

    Owner CAN access DRAFT lesson playback (subscription not required for owner).
    Non-owner/non-subscribed user should get 403 (subscription_required) or 404.
    """
    course = course_factory(label="draft-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="draft-playback-lesson")
    lesson_id = lesson.lesson_id

    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    owner_playback = api.get_playback(course_id, lesson_id)
    assert owner_playback.status_code == 200, (
        f"Owner should get 200 for DRAFT course, got {owner_playback.status_code}: {owner_playback.text}"
    )
    owner_body = owner_playback.json()
    assert "url" in owner_body, f"Expected presigned URL in response: {owner_body}"

    alt_playback = alt_api.get_playback(course_id, lesson_id)
    assert alt_playback.status_code in (403, 404), (
        f"Expected 403 or 404 for non-owner on DRAFT course, got {alt_playback.status_code}: {alt_playback.text}"
    )
    if alt_playback.status_code == 403:
        alt_body = alt_playback.json()
        assert alt_body.get("code") in ["forbidden", "subscription_required"], (
            f"Expected 'forbidden' or 'subscription_required', got {alt_body.get('code')}"
        )

    api.delete_course(course_id)
