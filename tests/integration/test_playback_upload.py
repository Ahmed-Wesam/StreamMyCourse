"""S4 playback + upload-url tests, including a real presigned PUT round-trip
(marked slow because it actually writes a few bytes to the integ S3 bucket --
the session-end safety net cleans them up)."""

from __future__ import annotations

import base64
import httpx
import pytest

from helpers.api import ApiClient

# Tiny valid JPEG (1×1 px) for lesson-thumbnail PUT smoke test.
_TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/"
    "2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/"
    "wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
)


# --- Playback gating --------------------------------------------------------------


def test_playback_when_lesson_not_ready_returns_400(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    lesson = lesson_factory(course.course_id)
    resp = api.get_playback(course.course_id, lesson.lesson_id)
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("code") == "bad_request"
    assert "ready" in body.get("message", "").lower()


def test_playback_for_unknown_lesson_returns_404(api: ApiClient, course_factory):
    course = course_factory()
    resp = api.get_playback(course.course_id, "lesson-does-not-exist")
    assert resp.status_code == 404
    assert resp.json().get("code") == "not_found"


# --- Upload URL shape --------------------------------------------------------------


def test_upload_url_returns_presigned_url_and_records_video_key(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert resp.status_code == 200
    body = resp.json()

    # Presigned URL signature: query string carries SigV4 parameters.
    assert body["uploadUrl"].startswith("https://")
    assert "X-Amz-Signature" in body["uploadUrl"]

    # Video key: {courseId}/lessons/{lessonId}/video/{uuid}.mp4
    assert body["videoKey"].startswith(
        f"{course.course_id}/lessons/{lesson.lesson_id}/video/"
    )
    assert body["videoKey"].endswith(".mp4")

    # Lesson should now reflect the recorded videoKey + pending status.
    listing = api.list_lessons(course.course_id)
    assert listing.status_code == 200
    items = {item["id"]: item for item in listing.json()}
    assert lesson.lesson_id in items
    item = items[lesson.lesson_id]
    assert "videoKey" not in item
    assert item["videoStatus"] == "pending"


def test_upload_url_for_unknown_lesson_returns_404(api: ApiClient, course_factory):
    course = course_factory()
    resp = api.get_upload_url(course_id=course.course_id, lesson_id="lesson-does-not-exist")
    assert resp.status_code == 404
    assert resp.json().get("code") == "not_found"


def test_upload_url_rejects_non_video_content_type(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    lesson = lesson_factory(course.course_id)
    resp = api.get_upload_url(
        course_id=course.course_id,
        lesson_id=lesson.lesson_id,
        content_type="application/octet-stream",
    )
    assert resp.status_code == 400
    assert resp.json().get("code") == "bad_request"


def test_lesson_thumbnail_upload_url_rejects_non_image_content_type(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    lesson = lesson_factory(course.course_id)
    resp = api.get_lesson_thumbnail_upload_url(
        course_id=course.course_id,
        lesson_id=lesson.lesson_id,
        content_type="video/mp4",
    )
    assert resp.status_code == 400
    assert resp.json().get("code") == "bad_request"


# --- Real upload round-trip (slow) -------------------------------------------------


@pytest.mark.slow
def test_full_upload_round_trip_to_s3_then_playback(
    api: ApiClient, course_factory, lesson_factory
):
    """End-to-end upload: presigned PUT to integ S3, mark ready, fetch playback URL.

    The integ video bucket has a CORS rule that allows PUT, but here we issue
    the PUT from outside a browser so CORS doesn't apply -- this validates the
    presigned URL itself (signature + bucket reachability).
    """
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200
    upload_url = upload_resp.json()["uploadUrl"]

    # Send a small fake video payload. MVP API does not validate MP4 contents.
    body = b"\x00" * 256
    put = httpx.put(upload_url, content=body, headers={"content-type": "video/mp4"}, timeout=30.0)
    assert put.status_code == 200, f"S3 PUT failed: {put.status_code} {put.text}"

    # Mark the lesson ready -> get playback URL.
    ready = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert ready.status_code == 200

    playback = api.get_playback(course.course_id, lesson.lesson_id)
    assert playback.status_code == 200
    playback_url = playback.json()["url"]
    assert playback_url.startswith("https://")
    assert "X-Amz-Signature" in playback_url

    # Fetch the bytes back via the presigned GET URL to confirm the object is real.
    fetched = httpx.get(playback_url, timeout=30.0)
    assert fetched.status_code == 200
    assert fetched.content == body


@pytest.mark.slow
def test_lesson_thumbnail_presigned_put_then_video_ready_lists_thumbnail_url(
    api: ApiClient, course_factory, lesson_factory
):
    """Lesson image: presign lessonThumbnail → PUT JPEG → video-ready with thumbnailKey → list has thumbnailUrl."""
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    video = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert video.status_code == 200
    vput = httpx.put(
        video.json()["uploadUrl"],
        content=b"\x00" * 128,
        headers={"content-type": "video/mp4"},
        timeout=30.0,
    )
    assert vput.status_code == 200

    thumb = api.get_lesson_thumbnail_upload_url(
        course_id=course.course_id,
        lesson_id=lesson.lesson_id,
    )
    assert thumb.status_code == 200
    thumb_json = thumb.json()
    assert thumb_json["thumbnailKey"].startswith(
        f"{course.course_id}/lessons/{lesson.lesson_id}/thumbnail/"
    )
    tput = httpx.put(
        thumb_json["uploadUrl"],
        content=_TINY_JPEG,
        headers={"content-type": "image/jpeg"},
        timeout=30.0,
    )
    assert tput.status_code == 200

    ready = api.mark_video_ready(
        course.course_id,
        lesson.lesson_id,
        thumbnail_key=thumb_json["thumbnailKey"],
    )
    assert ready.status_code == 200

    listing = api.list_lessons(course.course_id)
    assert listing.status_code == 200
    row = next(i for i in listing.json() if i["id"] == lesson.lesson_id)
    url = row.get("thumbnailUrl") or ""
    assert url.startswith("https://")
    assert "X-Amz-Signature" in url
