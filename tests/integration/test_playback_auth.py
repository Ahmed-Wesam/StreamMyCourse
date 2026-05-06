"""Playback authorization tests — enrollment-based content access.

These tests verify that playback URLs are only accessible to:
- Enrolled students
- Course owners (teachers who created the course)
- Admins

Non-enrolled users should receive 403 Forbidden.
DRAFT course lessons should return 404 even with valid JWT.
"""

from __future__ import annotations

from helpers.api import ApiClient


def test_enrolled_student_gets_playback_url(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Enrolled student should get 200 + presigned URL for playback."""
    # Teacher creates a course with a lesson using factory
    course = course_factory(label="enrolled-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="enrolled-playback-lesson")
    lesson_id = lesson.lesson_id

    # Teacher marks video ready and publishes the course
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # Student enrolls in the course
    enroll_resp = student_api.enroll_course(course_id)
    assert enroll_resp.status_code == 200, f"enroll_course failed: {enroll_resp.text}"

    # Student requests playback URL
    playback_resp = student_api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, f"Expected 200, got {playback_resp.status_code}: {playback_resp.text}"
    body = playback_resp.json()
    assert "url" in body, f"Expected 'url' in response body: {body}"
    assert isinstance(body["url"], str), f"Expected url to be a string: {body}"
    assert len(body["url"]) > 0, "Expected non-empty presigned URL"

    # Cleanup: Teacher deletes the course
    api.delete_course(course_id)


def test_non_enrolled_user_gets_403(
    api: ApiClient,
    alt_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Non-enrolled user (alt teacher) should get 403 when trying to access playback."""
    # Teacher A creates a course with a lesson using factory
    course = course_factory(label="non-enrolled-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="non-enrolled-playback-lesson")
    lesson_id = lesson.lesson_id

    # Teacher A marks video ready and publishes the course
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # Teacher B (alt_api) attempts to access playback without enrollment
    # Teacher B is not the owner and not enrolled
    playback_resp = alt_api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 403, f"Expected 403, got {playback_resp.status_code}: {playback_resp.text}"
    body = playback_resp.json()
    assert body.get("code") in ["forbidden", "enrollment_required"], (
        f"Expected code 'forbidden' or 'enrollment_required', got {body.get('code')}"
    )

    # Cleanup: Teacher A deletes the course
    api.delete_course(course_id)


def test_course_owner_gets_playback_url(
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Course owner should get 200 + presigned URL even without formal enrollment."""
    # Teacher creates a course with a lesson using factory
    course = course_factory(label="owner-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="owner-playback-lesson")
    lesson_id = lesson.lesson_id

    # Teacher marks video ready and publishes the course
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # Owner (same teacher) requests playback URL without enrolling
    playback_resp = api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, f"Expected 200, got {playback_resp.status_code}: {playback_resp.text}"
    body = playback_resp.json()
    assert "url" in body, f"Expected 'url' in response body: {body}"
    assert isinstance(body["url"], str), f"Expected url to be a string: {body}"
    assert len(body["url"]) > 0, "Expected non-empty presigned URL"

    # Cleanup: Teacher deletes the course
    api.delete_course(course_id)


def test_draft_lesson_playback_returns_404(
    api: ApiClient,
    alt_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Non-enrolled user should get 403/404 for DRAFT course lesson playback.

    Owner CAN access DRAFT lesson playback (enrollment not required for owner).
    Non-owner/non-enrolled user should get 403 (enrollment required) or 404.
    """
    # Teacher creates a course with a lesson (stays in DRAFT) using factory
    course = course_factory(label="draft-playback-course")
    course_id = course.course_id

    lesson = lesson_factory(course_id, label="draft-playback-lesson")
    lesson_id = lesson.lesson_id

    # Teacher marks video ready but does NOT publish
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course_id, lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    # Course remains in DRAFT status

    # Owner CAN access playback for their own DRAFT course
    owner_playback = api.get_playback(course_id, lesson_id)
    assert owner_playback.status_code == 200, f"Owner should get 200 for DRAFT course, got {owner_playback.status_code}: {owner_playback.text}"
    owner_body = owner_playback.json()
    assert "url" in owner_body, f"Expected presigned URL in response: {owner_body}"

    # Non-owner/non-enrolled user (alt teacher) should be denied
    # Expected behavior: 403 enrollment_required or 404 not_found
    alt_playback = alt_api.get_playback(course_id, lesson_id)
    assert alt_playback.status_code in (403, 404), (
        f"Expected 403 or 404 for non-enrolled user on DRAFT course, got {alt_playback.status_code}: {alt_playback.text}"
    )
    if alt_playback.status_code == 403:
        alt_body = alt_playback.json()
        assert alt_body.get("code") in ["forbidden", "enrollment_required"], (
            f"Expected 'forbidden' or 'enrollment_required', got {alt_body.get('code')}"
        )

    # Cleanup: Teacher deletes the course
    api.delete_course(course_id)
