"""Enrollment endpoint tests — subscription-only access (WS5).

POST /courses/{id}/enroll is deprecated for access; returns 403 subscription_required.
"""

from __future__ import annotations

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription, skip_if_student_has_subscription


def test_enroll_in_published_course_returns_subscription_required(
    student_api: ApiClient, api: ApiClient, course_factory, lesson_factory
) -> None:
    """POST /courses/{id}/enroll returns 403 subscription_required for published course."""
    course = course_factory(label="enrollment-blocked")
    lesson = lesson_factory(course.course_id, label="enrollment-blocked-lesson")

    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    resp = student_api.enroll_course(course.course_id)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "subscription_required"


def test_enroll_is_consistently_blocked(
    student_api: ApiClient, api: ApiClient, course_factory, lesson_factory
) -> None:
    """Repeated enroll attempts remain 403 subscription_required."""
    course = course_factory(label="enrollment-idempotent-blocked")
    lesson = lesson_factory(course.course_id, label="idempotent-blocked-lesson")

    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200

    for _ in range(2):
        resp = student_api.enroll_course(course.course_id)
        assert resp.status_code == 403, resp.text
        assert resp.json().get("code") == "subscription_required"


def test_enroll_in_draft_course_fails(
    student_api: ApiClient, api: ApiClient, course_factory
) -> None:
    """Enrolling in DRAFT course returns 404 (not_found)."""
    course = course_factory(label="enrollment-draft-course")

    resp = student_api.enroll_course(course.course_id)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "not_found"


def test_get_course_shows_has_access_after_subscription(
    api_base_url: str,
    student_api: ApiClient,
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """GET /courses/{id} includes hasAccess=True after mock subscription IPN."""
    course = course_factory(label="enrollment-access-flag")
    lesson = lesson_factory(course.course_id, label="access-flag-lesson")

    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200

    before_resp = student_api.get_course(course.course_id)
    assert before_resp.status_code == 200
    before_body = before_resp.json()
    if before_body.get("hasAccess") is True:
        after_body = before_body
    else:
        skip_if_student_has_subscription(student_api, course.course_id, lesson.lesson_id)
        assert before_body.get("hasAccess") is False
        assert before_body.get("enrolled") is False

        ensure_student_subscription(
            api_base_url, student_api, course.course_id, lesson.lesson_id
        )
        after_resp = student_api.get_course(course.course_id)
        assert after_resp.status_code == 200
        after_body = after_resp.json()

    assert after_body.get("hasAccess") is True
    assert after_body.get("enrolled") is True


def test_cannot_enroll_in_nonexistent_course(student_api: ApiClient) -> None:
    """404 for enrollment in unknown course ID."""
    fake_course_id = "nonexistent-course-id-12345"

    resp = student_api.enroll_course(fake_course_id)
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "not_found"
