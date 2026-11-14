"""Deployed API round-trips course/lesson/default module/course delete against Aurora DSQL."""

from __future__ import annotations

from helpers.api import ApiClient
from helpers.module_contract import (
    require_course_modules_list,
    require_lessons_include_module_fields,
)


def test_create_and_read_course_round_trips(api: ApiClient, course_factory):
    """POST /courses followed by GET /courses/{id} must succeed."""
    course = course_factory(description="dsql-smoke")

    got = api.get_course(course.course_id)
    assert got.status_code == 200, (
        f"GET /courses/{course.course_id} expected 200, got "
        f"{got.status_code}: {got.text}"
    )
    body = got.json()
    assert body["id"] == course.course_id
    assert body["title"] == course.title
    assert body["description"] == "dsql-smoke"
    assert body["status"] == "DRAFT"


def test_lesson_create_under_course(
    api: ApiClient, course_factory, lesson_factory
):
    """Creating a lesson must succeed (FK: lessons.course_id -> courses.id)."""
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    listing = api.list_lessons(course.course_id)
    raw = require_lessons_include_module_fields(listing)
    lesson_ids = {item["id"] for item in raw}
    assert lesson.lesson_id in lesson_ids, (
        f"lesson {lesson.lesson_id} not in GET /courses/{course.course_id}/lessons"
    )


def test_course_create_includes_default_module(api: ApiClient, course_factory):
    """POST /courses must leave a default ``course_modules`` row (module_order 0)."""
    course = course_factory(description="dsql-smoke")
    r = api.list_course_modules(course.course_id)
    mods = require_course_modules_list(r)
    assert len(mods) >= 1
    assert mods[0]["order"] == 0


def test_delete_course_cascades_modules_and_lessons(
    api: ApiClient, course_factory, lesson_factory
):
    course = course_factory()
    lesson_factory(course.course_id)
    require_course_modules_list(api.list_course_modules(course.course_id))
    assert api.delete_course(course.course_id).status_code == 200
    assert api.get_course(course.course_id).status_code == 404
