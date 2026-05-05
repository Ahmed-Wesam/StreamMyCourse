"""S3 publish-gate, video-ready, and full publish-flow tests."""

from __future__ import annotations

import base64
import os

import httpx
import pytest

from helpers.api import ApiClient

# Tiny valid JPEG (1×1 px) for lesson-thumbnail PUT (same as test_playback_upload).
_TINY_JPEG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/"
    "2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/"
    "wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/"
    "8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
)


def test_publish_without_any_ready_lesson_returns_400(
    api: ApiClient, course_factory, lesson_factory
):
    """publish_course in service.py raises BadRequest unless at least one lesson is ready."""
    course = course_factory()
    lesson_factory(course.course_id)  # has no videoKey, status='pending'
    resp = api.publish_course(course.course_id)
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("code") == "bad_request"
    assert "ready" in body.get("message", "").lower()


def test_publish_without_any_lessons_returns_400(api: ApiClient, course_factory):
    course = course_factory()
    resp = api.publish_course(course.course_id)
    assert resp.status_code == 400
    assert resp.json().get("code") == "bad_request"


def test_video_ready_without_upload_returns_400(
    api: ApiClient, course_factory, lesson_factory
):
    """mark_lesson_video_ready raises BadRequest if videoKey is empty."""
    course = course_factory()
    lesson = lesson_factory(course.course_id)
    resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
    assert resp.status_code == 400
    body = resp.json()
    assert body.get("code") == "bad_request"
    assert "video" in body.get("message", "").lower()


def test_video_ready_for_unknown_lesson_returns_404(
    api: ApiClient, course_factory
):
    course = course_factory()
    resp = api.mark_video_ready(course.course_id, "lesson-does-not-exist")
    assert resp.status_code == 404
    assert resp.json().get("code") == "not_found"


def test_full_publish_flow_appears_in_catalog(
    api: ApiClient, course_factory, lesson_factory
):
    """Happy path: create course + lesson -> upload-url (records videoKey) ->
    mark video ready -> publish -> course shows up in public catalog."""
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    # 1. Get an upload URL. This records the videoKey on the lesson but does
    #    NOT actually upload anything to S3 -- we don't need a real video for
    #    the catalog flow because MVP uses a trust model.
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200
    upload_body = upload_resp.json()
    assert upload_body["uploadUrl"]
    assert upload_body["videoKey"].startswith(
        f"{course.course_id}/lessons/{lesson.lesson_id}/video/"
    )

    # 2. Lesson thumbnail + mark the lesson ready (videoKey set + optional thumb).
    thumb = api.get_lesson_thumbnail_upload_url(
        course_id=course.course_id,
        lesson_id=lesson.lesson_id,
    )
    assert thumb.status_code == 200
    thumb_json = thumb.json()
    tput = httpx.put(
        thumb_json["uploadUrl"],
        content=_TINY_JPEG,
        headers={"content-type": "image/jpeg"},
        timeout=30.0,
    )
    assert tput.status_code == 200
    ready_resp = api.mark_video_ready(
        course.course_id,
        lesson.lesson_id,
        thumbnail_key=thumb_json["thumbnailKey"],
    )
    assert ready_resp.status_code == 200
    assert ready_resp.json()["videoStatus"] == "ready"

    # 3. Publish. Should succeed because the lesson is now ready.
    publish_resp = api.publish_course(course.course_id)
    assert publish_resp.status_code == 200
    assert publish_resp.json()["status"] == "PUBLISHED"

    # 4. Course should now appear in the public catalog.
    listing = api.list_courses()
    assert listing.status_code == 200
    ids_in_listing = {item["id"] for item in listing.json()}
    assert course.course_id in ids_in_listing

    # 5. GET /courses/{id} should reflect PUBLISHED.
    detail = api.get_course(course.course_id)
    assert detail.status_code == 200
    assert detail.json()["status"] == "PUBLISHED"

    # 6. Anonymous GET /courses/{id} and /lessons (no auth header): catalog + thumbnails, no videoKey.
    base = str(api.raw.base_url).rstrip("/")
    with httpx.Client(base_url=base, timeout=30.0) as anon:
        detail = anon.get(f"/courses/{course.course_id}")
        assert detail.status_code == 200
        assert detail.json().get("status") == "PUBLISHED"
        listing = anon.get(f"/courses/{course.course_id}/lessons")
        assert listing.status_code == 200
        rows = listing.json()
        assert isinstance(rows, list) and len(rows) >= 1
        for row in rows:
            assert "videoKey" not in row
        row0 = next(r for r in rows if r["id"] == lesson.lesson_id)
        url = row0.get("thumbnailUrl") or ""
        assert url.startswith("https://")
        assert "X-Amz-Signature" in url


@pytest.mark.skipif(
    not os.environ.get("INTEG_COGNITO_JWT", "").strip(),
    reason="Set INTEG_COGNITO_JWT to test draft course visibility (requires auth to distinguish anonymous users)",
)
def test_anonymous_get_draft_course_returns_404(api: ApiClient, course_factory):
    course = course_factory()
    base = str(api.raw.base_url).rstrip("/")
    with httpx.Client(base_url=base, timeout=30.0) as anon:
        r = anon.get(f"/courses/{course.course_id}")
        assert r.status_code == 404
        r2 = anon.get(f"/courses/{course.course_id}/lessons")
        assert r2.status_code == 404
