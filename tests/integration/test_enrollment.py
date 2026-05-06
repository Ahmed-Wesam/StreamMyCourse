"""Enrollment flow edge case tests.

Tests enrollment behavior including:
- Successful enrollment in published courses
- Idempotent enrollment (enrolling twice)
- Enrollment in draft courses (should fail)
- Enrollment flag in course details
- Enrollment in non-existent courses
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient


def test_enroll_in_published_course_succeeds(
    student_api: ApiClient, api: ApiClient, course_factory, lesson_factory
) -> None:
    """POST /courses/{id}/enroll returns 200 for published course."""
    # Teacher creates a course with a lesson
    course = course_factory(label="enrollment-success")
    lesson = lesson_factory(course.course_id, label="enrollment-lesson")

    # Get upload URL to register videoKey, then mark ready (required for publish)
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    # Publish the course
    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # Student enrolls in the published course
    resp = student_api.enroll_course(course.course_id)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["courseId"] == course.course_id
    assert body["enrolled"] is True


def test_enroll_is_idempotent(
    student_api: ApiClient, api: ApiClient, course_factory, lesson_factory
) -> None:
    """Enrolling twice returns 200 both times (idempotent)."""
    # Teacher creates a course with a lesson
    course = course_factory(label="enrollment-idempotent")
    lesson = lesson_factory(course.course_id, label="idempotent-lesson")

    # Get upload URL to register videoKey, then mark ready and publish
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # First enrollment
    resp1 = student_api.enroll_course(course.course_id)
    assert resp1.status_code == 200, f"First enroll failed: {resp1.status_code} {resp1.text}"
    body1 = resp1.json()
    assert body1["courseId"] == course.course_id
    assert body1["enrolled"] is True

    # Second enrollment (idempotent - should also succeed)
    resp2 = student_api.enroll_course(course.course_id)
    assert resp2.status_code == 200, f"Second enroll failed: {resp2.status_code} {resp2.text}"
    body2 = resp2.json()
    assert body2["courseId"] == course.course_id
    assert body2["enrolled"] is True


def test_enroll_in_draft_course_fails(
    student_api: ApiClient, api: ApiClient, course_factory
) -> None:
    """Enrolling in DRAFT course returns 404 (per discovery notes: not_found)."""
    # Teacher creates a course but does NOT publish it (stays in DRAFT)
    course = course_factory(label="enrollment-draft-course")
    # No lessons, no publish - stays in DRAFT status

    # Student attempts to enroll in draft course
    resp = student_api.enroll_course(course.course_id)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "not_found"


def test_get_course_shows_enrolled_true_after_enroll(
    student_api: ApiClient, api: ApiClient, course_factory, lesson_factory
) -> None:
    """GET /courses/{id} includes enrolled=True flag after enrollment."""
    # Teacher creates a course with a lesson
    course = course_factory(label="enrollment-flag-check")
    lesson = lesson_factory(course.course_id, label="flag-check-lesson")

    # Get upload URL to register videoKey, then mark ready and publish
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # Before enrollment: course should show enrolled=False
    before_resp = student_api.get_course(course.course_id)
    assert before_resp.status_code == 200
    before_body = before_resp.json()
    assert before_body.get("enrolled") is False

    # Student enrolls
    enroll_resp = student_api.enroll_course(course.course_id)
    assert enroll_resp.status_code == 200, f"enroll failed: {enroll_resp.text}"

    # After enrollment: course should show enrolled=True
    after_resp = student_api.get_course(course.course_id)
    assert after_resp.status_code == 200
    after_body = after_resp.json()
    assert after_body.get("enrolled") is True


def test_cannot_enroll_in_nonexistent_course(student_api: ApiClient) -> None:
    """404 for enrollment in unknown course ID."""
    fake_course_id = "nonexistent-course-id-12345"

    resp = student_api.enroll_course(fake_course_id)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "not_found"
