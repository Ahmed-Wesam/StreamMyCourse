"""Progress service integration tests — full coverage for lesson progress tracking.

These tests verify the progress service behavior including:
- Empty progress for new enrollments
- Progress persistence and retrieval
- Validation rules (mutually exclusive flags, negative position)
- Position slack handling (30 seconds beyond duration)
- Course-level progress aggregation
- Auto-completion at 92% ratio threshold
"""

from __future__ import annotations

import os

from helpers.api import ApiClient
from helpers.factories import CourseHandle, LessonHandle


def _require_jwts() -> None:
    """Ensure all 3 JWTs are available; exit if not (per spec: fail, don't skip)."""
    required = [
        "INTEGRATION_COGNITO_JWT",
        "INTEGRATION_COGNITO_JWT_ALT",
        "INTEGRATION_COGNITO_JWT_STUDENT",
    ]
    missing = [name for name in required if not os.environ.get(name, "").strip()]
    if missing:
        raise SystemExit(f"Missing required JWT environment variables: {missing}")


def _create_enrolled_course(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> tuple[str, str]:
    """Helper to create a published course with a lesson and enroll student.

    Returns (course_id, lesson_id).
    """
    # 1. Create a course
    course = course_factory(label="progress-enrolled")

    # 2. Create a lesson
    lesson = lesson_factory(course.course_id, label="progress-lesson")

    # 3. Mark video ready (required for publish)
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    # 4. Publish the course
    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # 5. Enroll the student
    enroll_resp = student_api.enroll_course(course.course_id)
    assert enroll_resp.status_code in (200, 201), f"enroll failed: {enroll_resp.text}"

    return (course.course_id, lesson.lesson_id)


def test_get_course_progress_empty(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """GET /courses/{id}/progress returns empty progress for new enrollment."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api, student_api, course_factory, lesson_factory
    )

    resp = student_api.get_course_progress(course_id)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["courseId"] == course_id
    assert body["totalReadyLessons"] >= 1
    assert body["completedCount"] == 0
    assert body["percentComplete"] == 0.0

    # Find the lesson in the response
    lesson_progress = None
    for lp in body["lessons"]:
        if lp["lessonId"] == lesson_id:
            lesson_progress = lp
            break

    assert lesson_progress is not None, f"Lesson {lesson_id} not found in progress"
    assert lesson_progress["completed"] is False
    assert lesson_progress["lastPositionSec"] == 0


def test_update_lesson_progress_persists(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """PUT progress persists and GET returns updated data."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api, student_api, course_factory, lesson_factory
    )

    # Update progress to position 45 seconds of 100 second video
    update_resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=45,
        duration=100,
    )
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"

    update_body = update_resp.json()
    assert update_body["ok"] is True
    assert update_body["lessonProgress"]["lastPositionSec"] == 45
    assert update_body["lessonProgress"]["completed"] is False

    # Verify GET returns the persisted data
    get_resp = student_api.get_course_progress(course_id)
    assert get_resp.status_code == 200

    get_body = get_resp.json()
    lesson_progress = None
    for lp in get_body["lessons"]:
        if lp["lessonId"] == lesson_id:
            lesson_progress = lp
            break

    assert lesson_progress is not None
    assert lesson_progress["lastPositionSec"] == 45
    assert lesson_progress["completed"] is False


def test_mark_complete_and_incomplete_mutual_exclusion(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Verify 400 when both markComplete and markIncomplete flags are set."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api, student_api, course_factory, lesson_factory
    )

    resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=30,
        duration=100,
        mark_complete=True,
        mark_incomplete=True,
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"

    body = resp.json()
    # Controller validates this and returns generic bad_request (before service layer)
    assert body.get("code") == "bad_request"


def test_negative_position_returns_400(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Validation rejects negative position."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api, student_api, course_factory, lesson_factory
    )

    resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=-10,
        duration=100,
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"


def test_position_exceeds_duration_with_slack(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Position can exceed duration by slack amount (30s)."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api, student_api, course_factory, lesson_factory
    )

    # Position at exactly duration + 30 (the max slack allowed)
    duration = 100
    position = duration + 30  # 130 seconds

    resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=position,
        duration=duration,
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body["ok"] is True
    assert body["lessonProgress"]["lastPositionSec"] == position

    # Position exceeding slack should fail
    position_too_far = duration + 31
    fail_resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=position_too_far,
        duration=duration,
    )
    assert fail_resp.status_code == 400, f"Expected 400, got {fail_resp.status_code}"


def test_progress_aggregates_multiple_lessons(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """GET course progress aggregates all lessons."""
    _require_jwts()

    # Create course with multiple lessons
    course = course_factory(label="multi-lesson-progress")

    # Create 3 lessons
    lesson1 = lesson_factory(course.course_id, label="lesson-one")
    lesson2 = lesson_factory(course.course_id, label="lesson-two")
    lesson3 = lesson_factory(course.course_id, label="lesson-three")

    # Mark videos ready and publish
    for lesson in [lesson1, lesson2, lesson3]:
        upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
        assert upload_resp.status_code == 200
        api.mark_video_ready(course.course_id, lesson.lesson_id)

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200

    # Student enrolls
    enroll_resp = student_api.enroll_course(course.course_id)
    assert enroll_resp.status_code == 200

    # Complete lesson1 and lesson2, leave lesson3 incomplete
    for lesson in [lesson1, lesson2]:
        resp = student_api.update_lesson_progress(
            course.course_id,
            lesson.lesson_id,
            position=100,
            duration=100,
            mark_complete=True,
        )
        assert resp.status_code == 200

    # Partial progress on lesson3
    resp = student_api.update_lesson_progress(
        course.course_id,
        lesson3.lesson_id,
        position=50,
        duration=100,
    )
    assert resp.status_code == 200

    # Get aggregated progress
    agg_resp = student_api.get_course_progress(course.course_id)
    assert agg_resp.status_code == 200

    agg_body = agg_resp.json()
    assert agg_body["totalReadyLessons"] == 3
    assert agg_body["completedCount"] == 2
    assert agg_body["percentComplete"] == 66.67

    # Verify all lessons appear in response
    lesson_ids = {lp["lessonId"] for lp in agg_body["lessons"]}
    assert lesson1.lesson_id in lesson_ids
    assert lesson2.lesson_id in lesson_ids
    assert lesson3.lesson_id in lesson_ids


def test_auto_complete_threshold(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Progress auto-completes at 92% ratio."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api, student_api, course_factory, lesson_factory
    )

    duration = 100

    # Position at 91% should NOT auto-complete (below 92% threshold)
    resp_91 = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=91,
        duration=duration,
    )
    assert resp_91.status_code == 200
    body_91 = resp_91.json()
    assert body_91["lessonProgress"]["completed"] is False

    # Position at 92% should auto-complete (at threshold)
    resp_92 = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=92,
        duration=duration,
    )
    assert resp_92.status_code == 200
    body_92 = resp_92.json()
    assert body_92["lessonProgress"]["completed"] is True

    # Position at 95% should auto-complete (above threshold)
    resp_95 = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=95,
        duration=duration,
    )
    assert resp_95.status_code == 200
    body_95 = resp_95.json()
    assert body_95["lessonProgress"]["completed"] is True
