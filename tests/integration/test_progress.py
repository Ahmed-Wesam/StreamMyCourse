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

import httpx

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription, skip_if_student_has_subscription
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


def _create_subscribed_course(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> tuple[str, str]:
    """Helper to create a published course with a lesson and grant subscription access.

    Returns (course_id, lesson_id).
    """
    course = course_factory(label="progress-subscribed")
    lesson = lesson_factory(course.course_id, label="progress-lesson")

    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    ensure_student_subscription(
        api_base_url, student_api, course.course_id, lesson.lesson_id
    )
    return (course.course_id, lesson.lesson_id)


def _create_published_course_with_lesson(
    api: ApiClient,
    course_factory,
    lesson_factory,
    *,
    course_label: str,
    lesson_label: str,
) -> tuple[str, str]:
    """Helper to create a published course with one ready lesson.

    Returns (course_id, lesson_id).
    """
    course = course_factory(label=course_label)
    lesson = lesson_factory(course.course_id, label=lesson_label)

    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    return (course.course_id, lesson.lesson_id)


_create_enrolled_course = _create_subscribed_course


def test_get_course_progress_empty(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """GET /courses/{id}/progress returns empty progress for a new subscriber."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
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
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """PUT progress persists and GET returns updated data."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
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
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Verify 400 when both markComplete and markIncomplete flags are set."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
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
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Validation rejects negative position."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
    )

    resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=-10,
        duration=100,
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"


def test_position_exceeds_duration_with_slack(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Position can exceed duration by slack amount (30s)."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
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
    api_base_url: str,
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

    # Grant platform subscription
    ensure_student_subscription(
        api_base_url, student_api, course.course_id, lesson1.lesson_id
    )

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
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Progress auto-completes at 92% ratio."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
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


def test_cannot_record_progress_for_lesson_in_other_course(
    api_base_url: str,
    api: ApiClient,
    alt_api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
    alt_course_factory,
    alt_lesson_factory,
) -> None:
    """Student with subscription in Course A cannot update progress for a lesson in Course B via (A, B_lesson) pair."""
    _require_jwts()

    course_a_id, _lesson_a1_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="cross-course-hack-A",
        lesson_label="cross-course-hack-A-L1",
    )
    course_b_id, lesson_b1_id = _create_published_course_with_lesson(
        alt_api,
        alt_course_factory,
        alt_lesson_factory,
        course_label="cross-course-hack-B",
        lesson_label="cross-course-hack-B-L1",
    )

    ensure_student_subscription(api_base_url, student_api, course_a_id, _lesson_a1_id)

    resp = student_api.update_lesson_progress(
        course_a_id,
        lesson_b1_id,
        position=10,
        duration=100,
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "not_found"
    assert "lesson" in body.get("message", "").lower() or body.get("message")

    # Ensure the B course exists to avoid false positives in this test.
    assert course_b_id


def test_cannot_record_progress_using_other_instructors_lesson_id(
    api: ApiClient,
    alt_api: ApiClient,
    course_factory,
    lesson_factory,
    alt_course_factory,
    alt_lesson_factory,
) -> None:
    """Course owner cannot update progress for their course using another instructor's lesson ID."""
    _require_jwts()

    course_m_id, _lesson_m1_id = _create_published_course_with_lesson(
        alt_api,
        alt_course_factory,
        alt_lesson_factory,
        course_label="cross-instructor-course-M",
        lesson_label="cross-instructor-course-M-L1",
    )
    _course_v_id, lesson_v1_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="cross-instructor-course-V",
        lesson_label="cross-instructor-course-V-L1",
    )

    resp = alt_api.update_lesson_progress(
        course_m_id,
        lesson_v1_id,
        position=10,
        duration=100,
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "not_found"


def test_progress_update_does_not_leak_to_real_owning_course(
    api_base_url: str,
    api: ApiClient,
    alt_api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
    alt_course_factory,
    alt_lesson_factory,
) -> None:
    """Rejected cross-course update must not write progress into the lesson's real owning course."""
    _require_jwts()

    course_a_id, lesson_a1_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="no-leak-A",
        lesson_label="no-leak-A-L1",
    )
    course_b_id, lesson_b1_id = _create_published_course_with_lesson(
        alt_api,
        alt_course_factory,
        alt_lesson_factory,
        course_label="no-leak-B",
        lesson_label="no-leak-B-L1",
    )

    ensure_student_subscription(api_base_url, student_api, course_a_id, lesson_a1_id)

    hack_resp = student_api.update_lesson_progress(
        course_a_id,
        lesson_b1_id,
        position=10,
        duration=100,
    )
    assert hack_resp.status_code == 404
    assert hack_resp.json().get("code") == "not_found"

    # Platform subscription already grants access to course B; progress must remain zero.
    get_b = student_api.get_course_progress(course_b_id)
    assert get_b.status_code == 200, get_b.text
    body_b = get_b.json()
    lp = next((x for x in body_b["lessons"] if x["lessonId"] == lesson_b1_id), None)
    assert lp is not None
    assert lp["completed"] is False
    assert lp["lastPositionSec"] == 0


def test_unauthenticated_request_to_update_progress(
    api_base_url: str,
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """PUT progress without Authorization header returns 401 (gateway-enforced)."""
    _require_jwts()

    course_id, lesson_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="unauth-progress",
        lesson_label="unauth-progress-L1",
    )

    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        resp = client.put(
            f"/courses/{course_id}/lessons/{lesson_id}/progress",
            json={"position": 10, "duration": 100, "markComplete": False, "markIncomplete": False},
            headers={},  # explicit: no Authorization
        )
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"


def test_unenrolled_non_owner_cannot_update_progress(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Student without subscription (and not owner) cannot update progress (403 subscription_required)."""
    _require_jwts()

    course_id, lesson_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="unenrolled-update",
        lesson_label="unenrolled-update-L1",
    )
    skip_if_student_has_subscription(student_api, course_id, lesson_id)

    resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=10,
        duration=100,
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "subscription_required"


def test_random_lesson_id_returns_not_found(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Valid-but-random lesson UUID returns 404 not_found (no existence leakage)."""
    _require_jwts()

    course_id, _lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
    )
    random_lesson_id = "00000000-0000-0000-0000-000000000099"

    resp = student_api.update_lesson_progress(
        course_id,
        random_lesson_id,
        position=10,
        duration=100,
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body.get("code") == "not_found"


def test_invalid_uuid_in_path_params_returns_404(
    student_api: ApiClient,
) -> None:
    """Malformed UUIDs in either course_id or lesson_id return 404 (service guard)."""
    _require_jwts()

    resp_course = student_api.update_lesson_progress(
        "not-a-uuid",
        "00000000-0000-0000-0000-000000000099",
        position=10,
        duration=100,
    )
    assert resp_course.status_code == 404, f"Expected 404, got {resp_course.status_code}: {resp_course.text}"
    assert resp_course.json().get("code") == "not_found"

    resp_lesson = student_api.update_lesson_progress(
        "00000000-0000-0000-0000-000000000099",
        "not-a-uuid",
        position=10,
        duration=100,
    )
    assert resp_lesson.status_code == 404, f"Expected 404, got {resp_lesson.status_code}: {resp_lesson.text}"
    assert resp_lesson.json().get("code") == "not_found"


def test_idempotent_upsert(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Sending the same update payload twice is idempotent and results are stable."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
    )

    resp1 = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=45,
        duration=100,
    )
    assert resp1.status_code == 200, resp1.text
    body1 = resp1.json()
    assert body1.get("ok") is True

    resp2 = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=45,
        duration=100,
    )
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert body2.get("ok") is True

    assert body1["lessonProgress"] == body2["lessonProgress"]

    get_resp = student_api.get_course_progress(course_id)
    assert get_resp.status_code == 200, get_resp.text
    get_body = get_resp.json()
    lp = next((x for x in get_body["lessons"] if x["lessonId"] == lesson_id), None)
    assert lp is not None
    assert lp["lastPositionSec"] == 45
    assert lp["completed"] is False


def test_mark_complete_then_incomplete_clears_completed_at(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Explicit complete then explicit incomplete clears completedAt in the persisted state."""
    _require_jwts()

    course_id, lesson_id = _create_enrolled_course(
        api_base_url, api, student_api, course_factory, lesson_factory
    )

    complete_resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=100,
        duration=100,
        mark_complete=True,
    )
    assert complete_resp.status_code == 200, complete_resp.text
    complete_body = complete_resp.json()
    lp1 = complete_body["lessonProgress"]
    assert lp1["completed"] is True
    assert "completedAt" in lp1 and lp1["completedAt"]

    incomplete_resp = student_api.update_lesson_progress(
        course_id,
        lesson_id,
        position=0,
        duration=100,
        mark_incomplete=True,
    )
    assert incomplete_resp.status_code == 200, incomplete_resp.text
    incomplete_body = incomplete_resp.json()
    lp2 = incomplete_body["lessonProgress"]
    assert lp2["completed"] is False
    assert "completedAt" not in lp2 or lp2["completedAt"] is None

    get_resp = student_api.get_course_progress(course_id)
    assert get_resp.status_code == 200, get_resp.text
    get_body = get_resp.json()
    lp3 = next((x for x in get_body["lessons"] if x["lessonId"] == lesson_id), None)
    assert lp3 is not None
    assert lp3["completed"] is False
    assert "completedAt" not in lp3


def test_get_course_progress_unenrolled_returns_403(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Student without subscription (and not owner) cannot read progress (403 subscription_required)."""
    _require_jwts()

    course_id, lesson_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="unenrolled-read-progress",
        lesson_label="unenrolled-read-progress-L1",
    )
    skip_if_student_has_subscription(student_api, course_id, lesson_id)

    resp = student_api.get_course_progress(course_id)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    assert resp.json().get("code") == "subscription_required"


def test_get_course_progress_for_random_course_returns_4xx(
    student_api: ApiClient,
) -> None:
    """Random course_id returns 403 due to auth check firing before course existence checks."""
    _require_jwts()

    random_course_id = "00000000-0000-0000-0000-000000000199"
    resp = student_api.get_course_progress(random_course_id)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    assert resp.json().get("code") == "subscription_required"


def test_owner_can_view_own_course_progress(
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Teacher owner can view their own course progress without enrolling (200, empty progress)."""
    _require_jwts()

    course_id, _lesson_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="owner-view-progress",
        lesson_label="owner-view-progress-L1",
    )

    resp = api.get_course_progress(course_id)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert body["courseId"] == course_id
    assert body["totalReadyLessons"] >= 1
    assert body["completedCount"] == 0


def test_get_course_progress_does_not_include_other_courses_lessons(
    api_base_url: str,
    api: ApiClient,
    alt_api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
    alt_course_factory,
    alt_lesson_factory,
) -> None:
    """Progress read is scoped to course_id: lessons from other courses must not appear."""
    _require_jwts()

    course_a_id, lesson_a1_id = _create_published_course_with_lesson(
        api,
        course_factory,
        lesson_factory,
        course_label="progress-scope-A",
        lesson_label="progress-scope-A-L1",
    )
    course_b_id, lesson_b1_id = _create_published_course_with_lesson(
        alt_api,
        alt_course_factory,
        alt_lesson_factory,
        course_label="progress-scope-B",
        lesson_label="progress-scope-B-L1",
    )

    ensure_student_subscription(api_base_url, student_api, course_a_id, lesson_a1_id)

    upd_a = student_api.update_lesson_progress(course_a_id, lesson_a1_id, position=10, duration=100)
    assert upd_a.status_code == 200, upd_a.text
    upd_b = student_api.update_lesson_progress(course_b_id, lesson_b1_id, position=20, duration=100)
    assert upd_b.status_code == 200, upd_b.text

    get_a = student_api.get_course_progress(course_a_id)
    assert get_a.status_code == 200, get_a.text
    lessons_a = {x["lessonId"] for x in get_a.json()["lessons"]}
    assert lesson_a1_id in lessons_a
    assert lesson_b1_id not in lessons_a

    get_b = student_api.get_course_progress(course_b_id)
    assert get_b.status_code == 200, get_b.text
    lessons_b = {x["lessonId"] for x in get_b.json()["lessons"]}
    assert lesson_b1_id in lessons_b
    assert lesson_a1_id not in lessons_b
