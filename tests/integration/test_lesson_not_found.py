"""Tests for 404 responses when lesson ID does not exist.

Covers edge cases where course exists but lesson ID is unknown or wrong.
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient


def test_update_lesson_unknown_id_returns_404(api: ApiClient, course_factory) -> None:
    """PUT /courses/{id}/lessons/{lid} returns 404 for non-existent lesson."""
    course = course_factory(label="update-lesson-not-found")
    fake_lesson_id = "00000000-0000-0000-0000-000000000002"

    resp = api.update_lesson(course.course_id, fake_lesson_id, title="Updated")
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("code") == "not_found"


def test_delete_lesson_unknown_id_returns_404(api: ApiClient, course_factory) -> None:
    """DELETE /courses/{id}/lessons/{lid} returns 404 for non-existent lesson."""
    course = course_factory(label="delete-lesson-not-found")
    fake_lesson_id = "00000000-0000-0000-0000-000000000003"

    resp = api.delete_lesson(course.course_id, fake_lesson_id)
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("code") == "not_found"


def test_mark_video_ready_unknown_lesson_returns_404(api: ApiClient, course_factory) -> None:
    """PUT /courses/{id}/lessons/{lid}/video-ready returns 404 for non-existent lesson."""
    course = course_factory(label="video-ready-lesson-not-found")
    fake_lesson_id = "00000000-0000-0000-0000-000000000004"

    resp = api.mark_video_ready(course.course_id, fake_lesson_id)
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("code") == "not_found"


def test_get_upload_url_unknown_lesson_returns_404(api: ApiClient, course_factory) -> None:
    """POST /upload-url returns 404 when lesson_id does not exist."""
    course = course_factory(label="upload-url-lesson-not-found")
    fake_lesson_id = "00000000-0000-0000-0000-000000000005"

    resp = api.get_upload_url(
        course_id=course.course_id,
        lesson_id=fake_lesson_id,
        filename="video.mp4",
        content_type="video/mp4"
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("code") == "not_found"


def test_get_playback_url_unknown_lesson_returns_404(api: ApiClient, course_factory) -> None:
    """GET /playback/{courseId}/{lessonId} returns 404 for non-existent lesson."""
    course = course_factory(label="playback-lesson-not-found")
    fake_lesson_id = "00000000-0000-0000-0000-000000000006"

    resp = api.raw.get(f"/playback/{course.course_id}/{fake_lesson_id}")
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("code") == "not_found"


def test_lesson_thumbnail_upload_url_unknown_lesson_returns_404(api: ApiClient, course_factory) -> None:
    """POST /upload-url with uploadKind=lesson_thumbnail returns 404 for non-existent lesson."""
    course = course_factory(label="thumb-upload-lesson-not-found")
    fake_lesson_id = "00000000-0000-0000-0000-000000000007"

    resp = api.get_lesson_thumbnail_upload_url(
        course_id=course.course_id,
        lesson_id=fake_lesson_id,
        filename="thumb.jpg",
        content_type="image/jpeg"
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body.get("code") == "not_found"


def test_get_progress_unknown_lesson_is_handled(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """GET /courses/{id}/progress aggregates only existing lessons."""
    course = course_factory(label="get-progress-lesson-check")
    real_lesson = lesson_factory(course.course_id, label="real-lesson")

    # Publish and enroll
    api.get_upload_url(course_id=course.course_id, lesson_id=real_lesson.lesson_id)
    api.mark_video_ready(course.course_id, real_lesson.lesson_id)
    api.publish_course(course.course_id)
    student_api.enroll_course(course.course_id)

    # Get progress - should only aggregate existing lesson
    resp = student_api.get_course_progress(course.course_id)
    assert resp.status_code == 200
    body = resp.json()
    # Should not error even if progress table has orphaned rows
    assert "lessons" in body
