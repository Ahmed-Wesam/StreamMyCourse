"""S3 publish-gate, video-ready, and full publish-flow tests."""

from __future__ import annotations

from helpers.api import ApiClient


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

    # 2. Mark the lesson ready (now that videoKey is set).
    ready_resp = api.mark_video_ready(course.course_id, lesson.lesson_id)
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

    # 6. Anonymous preview includes lesson outline (no S3 keys).
    preview = api.get_course_preview(course.course_id)
    assert preview.status_code == 200
    pv = preview.json()
    assert pv.get("status") == "PUBLISHED"
    assert "lessonsPreview" in pv
    lp = pv["lessonsPreview"]
    assert isinstance(lp, list) and len(lp) >= 1
    assert set(lp[0].keys()) <= {"id", "title", "order"}
