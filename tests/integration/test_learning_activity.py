"""DSQL-4 S6: lesson completion activity feed and streak over HTTPS."""

from __future__ import annotations

import os

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription


def _require_jwts() -> None:
    if not os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip():
        raise SystemExit("Missing INTEGRATION_COGNITO_JWT_STUDENT")


def _published_lesson(api: ApiClient, course_factory, lesson_factory) -> tuple[str, str]:
    course = course_factory(label="activity-complete")
    lesson = lesson_factory(course.course_id, label="activity-lesson")
    assert api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id).status_code == 200
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200
    return course.course_id, lesson.lesson_id


def test_mark_complete_surfaces_on_me_activity_with_stable_completed_at(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    _require_jwts()
    course_id, lesson_id = _published_lesson(api, course_factory, lesson_factory)
    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

    complete = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=100,
        duration=100,
        mark_complete=True,
    )
    assert complete.status_code == 200, complete.text
    first_lp = complete.json()["lessonProgress"]
    assert first_lp["completed"] is True
    first_completed_at = first_lp.get("completedAt")
    assert first_completed_at

    activity = student_api.get_my_activity()
    assert activity.status_code == 200, activity.text
    body = activity.json()
    assert int(body.get("streakDays") or 0) >= 1
    items = body.get("items") or []
    hits = [
        i
        for i in items
        if i.get("kind") == "lesson_completion" and i.get("resourceId") == lesson_id
    ]
    assert hits, f"expected lesson_completion for {lesson_id}, items={items!r}"

    second = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=100,
        duration=100,
        mark_complete=True,
    )
    assert second.status_code == 200, second.text
    second_lp = second.json()["lessonProgress"]
    assert second_lp.get("completedAt") == first_completed_at
