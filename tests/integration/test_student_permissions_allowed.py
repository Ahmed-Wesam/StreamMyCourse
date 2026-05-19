"""Positive student permission tests — what students SHOULD be able to do.

These tests verify the student role can:
- Browse published course catalog
- View published course details
- View course lessons (for published courses)
- Enroll in published courses
- Access playback after subscription
- Update and view progress
- See student role in profile
"""

from __future__ import annotations


def test_student_can_list_courses(student_api, course_factory):
    """Student can GET /courses to browse the catalog."""
    # Ensure at least one published course exists (teacher creates it)
    course_factory(label="catalog-course", description="For catalog browsing")

    resp = student_api.list_courses()
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Catalog should contain courses (at minimum the one we just created)
    assert len(body) >= 1
    # Each course should have basic fields
    for course in body:
        assert "id" in course
        assert "title" in course
        assert "status" in course


def test_student_can_view_published_course(student_api, api, course_factory, lesson_factory):
    """Student can GET /courses/{id} for a PUBLISHED course."""
    # Teacher creates and publishes a course
    course = course_factory(label="published-course-view")
    lesson = lesson_factory(course.course_id, label="viewable-lesson")

    # Get upload URL to register videoKey, then mark ready (required by backend validation)
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    # Publish the course
    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # Student views the published course
    resp = student_api.get_course(course.course_id)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == course.course_id
    assert body["title"] == course.title
    assert body["status"] == "PUBLISHED"


def test_student_can_view_course_lessons(student_api, api, course_factory, lesson_factory):
    """Student can GET /courses/{id}/lessons for a PUBLISHED course."""
    # Teacher creates and publishes a course with lessons
    course = course_factory(label="course-with-lessons")
    lesson1 = lesson_factory(course.course_id, label="lesson-one")
    lesson2 = lesson_factory(course.course_id, label="lesson-two")

    # Get upload URL to register videoKey, then mark ready and publish
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson1.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson1.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    # Student lists lessons
    resp = student_api.list_lessons(course.course_id)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2
    lesson_ids = [str(item["id"]) for item in body]
    assert lesson1.lesson_id in lesson_ids
    assert lesson2.lesson_id in lesson_ids


def test_student_profile_shows_role_student(student_api):
    """Student's GET /users/me returns role="student"."""
    resp = student_api.get_users_me()
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("role") == "student"


def test_student_can_update_progress_and_view_aggregated(
    api_base_url: str,
    student_api, api, course_factory, lesson_factory
):
    """Student can PUT progress and GET aggregated course progress after subscription."""
    # Teacher creates, publishes a course with a lesson
    course = course_factory(label="progress-course")
    lesson = lesson_factory(course.course_id, label="progress-lesson")

    # Get upload URL to register videoKey, then mark ready and publish
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, f"get_upload_url failed: {upload_resp.text}"

    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready_resp.status_code == 200, f"mark_video_ready failed: {ready_resp.text}"

    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200, f"publish_course failed: {publish_resp.text}"

    from helpers.billing_access import ensure_student_subscription

    ensure_student_subscription(
        api_base_url, student_api, course.course_id, lesson.lesson_id
    )

    # Update progress for the lesson (watched 30 seconds of 60 second video)
    progress_resp = student_api.update_lesson_progress(
        course.course_id,
        lesson.lesson_id,
        position=30,
        duration=60,
    )
    assert progress_resp.status_code == 200
    progress_body = progress_resp.json()
    assert progress_body.get("ok") is True
    assert "lessonProgress" in progress_body
    assert progress_body["lessonProgress"]["lastPositionSec"] == 30

    # Get aggregated course progress
    agg_resp = student_api.get_course_progress(course.course_id)
    assert agg_resp.status_code == 200
    agg_body = agg_resp.json()
    # Should contain progress for the lesson we updated
    assert "lessons" in agg_body
    lesson_progress = None
    for lp in agg_body["lessons"]:
        if lp["lessonId"] == lesson.lesson_id:
            lesson_progress = lp
            break
    assert lesson_progress is not None
    assert lesson_progress["lastPositionSec"] == 30
    assert lesson_progress["completed"] is False
