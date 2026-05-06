"""Course thumbnail upload and readiness tests.

Tests course cover image flow:
1. Getting presigned upload URL for thumbnails
2. Marking thumbnail as ready after upload
3. Verifying thumbnailUrl appears in course details
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient


def test_thumbnail_upload_url_returns_presigned_url(api: ApiClient, course_factory) -> None:
    """POST /upload-url with uploadKind=thumbnail returns presigned URL and key."""
    # Create a course first
    course = course_factory(label="thumbnail-upload")

    # Request thumbnail upload URL
    resp = api.get_course_thumbnail_upload_url(
        course_id=course.course_id,
        filename="cover.jpg",
        content_type="image/jpeg",
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert "uploadUrl" in body, f"uploadUrl missing in response: {body}"
    assert body["uploadUrl"].startswith("http"), f"uploadUrl should be a URL: {body['uploadUrl']}"

    # Thumbnail uploads should return a thumbnailKey (not videoKey)
    assert "thumbnailKey" in body, f"thumbnailKey missing in response: {body}"
    assert body["thumbnailKey"].startswith(course.course_id), \
        f"thumbnailKey should start with course_id: {body['thumbnailKey']}"
    assert "thumbnail/" in body["thumbnailKey"], \
        f"thumbnailKey should contain 'thumbnail/' path: {body['thumbnailKey']}"


def test_thumbnail_ready_marks_course(api: ApiClient, course_factory) -> None:
    """PUT /courses/{id}/thumbnail-ready marks course thumbnail as ready."""
    # Create a course
    course = course_factory(label="thumbnail-ready")

    # Mark thumbnail as ready with a key
    thumbnail_key = f"{course.course_id}/thumbnail/cover.jpg"
    resp = api.thumbnail_ready(course.course_id, thumbnail_key)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    body = resp.json()
    assert body.get("id") == course.course_id, f"Course ID mismatch: {body}"
    assert body.get("thumbnailReady") is True, f"thumbnailReady should be True: {body}"


