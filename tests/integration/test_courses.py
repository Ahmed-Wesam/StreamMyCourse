"""S2 course lifecycle tests: CRUD and the catalog (PUBLISHED-only) filter."""

from __future__ import annotations

import uuid

from helpers.api import ApiClient
from helpers.factories import TEST_TITLE_PREFIX


def test_draft_course_is_not_in_public_catalog(api: ApiClient, course_factory):
    course = course_factory()
    listing = api.list_courses()
    assert listing.status_code == 200
    ids_in_listing = {item["id"] for item in listing.json()}
    assert course.course_id not in ids_in_listing, (
        "Draft courses must not appear in GET /courses (catalog is published-only)"
    )


def test_get_course_known_id_returns_full_record(api: ApiClient, course_factory):
    course = course_factory(description="seed description")
    resp = api.get_course(course.course_id)
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == course.course_id
    assert body["title"] == course.title
    assert body["description"] == "seed description"
    assert body["status"] == "DRAFT"


def test_get_course_unknown_id_returns_404(api: ApiClient):
    # Use a valid UUID that does not exist in the database
    unknown = "00000000-0000-0000-0000-000000000000"
    resp = api.get_course(unknown)
    assert resp.status_code == 404
    assert resp.json().get("code") == "not_found"


def test_update_course_metadata_is_reflected(api: ApiClient, course_factory):
    course = course_factory(description="before")
    new_title = f"{TEST_TITLE_PREFIX}updated-{uuid.uuid4()}"
    upd = api.update_course(course.course_id, title=new_title, description="after")
    assert upd.status_code == 200
    got = api.get_course(course.course_id)
    assert got.status_code == 200
    body = got.json()
    assert body["title"] == new_title
    assert body["description"] == "after"


def test_delete_course_removes_it_and_cascades_to_lessons(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    lesson = lesson_factory(course.course_id)
    # sanity: lesson exists
    listing = api.list_lessons(course.course_id)
    assert listing.status_code == 200
    assert any(item["id"] == lesson.lesson_id for item in listing.json())

    deleted = api.delete_course(course.course_id)
    assert deleted.status_code == 200

    # subsequent GET on the course returns 404
    got = api.get_course(course.course_id)
    assert got.status_code == 404

    # Lessons listing requires a course the caller may view; after delete the
    # course is gone, so the API returns 404 (not an empty list).
    after = api.list_lessons(course.course_id)
    assert after.status_code == 404
    assert after.json().get("code") == "not_found"


def test_update_lesson_title_is_reflected(api: ApiClient, course_factory, lesson_factory):
    course = course_factory()
    lesson = lesson_factory(course.course_id)
    new_title = f"{TEST_TITLE_PREFIX}updated-lesson-{uuid.uuid4()}"
    upd = api.update_lesson(course.course_id, lesson.lesson_id, title=new_title)
    assert upd.status_code == 200
    got = api.list_lessons(course.course_id)
    assert got.status_code == 200
    lessons = got.json()
    updated = next(item for item in lessons if item["id"] == lesson.lesson_id)
    assert updated["title"] == new_title


def test_update_lesson_unknown_returns_404(api: ApiClient, course_factory):
    course = course_factory()
    unknown_lesson_id = "00000000-0000-0000-0000-000000000000"
    resp = api.update_lesson(course.course_id, unknown_lesson_id, title="New Title")
    assert resp.status_code == 404
    assert resp.json().get("code") == "not_found"
