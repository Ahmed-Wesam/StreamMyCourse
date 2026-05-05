"""Catalog persistence smoke tests (PostgreSQL in managed dev/prod).

These tests assert that the deployed API can round-trip writes and reads when
the catalog is backed by PostgreSQL. The rest of the integration suite exercises
the same contract; this module adds a focused smoke for FK and metadata paths.

The tests assume:
- `INTEGRATION_API_BASE_URL` points at the deployed API
- The PostgreSQL schema (001_initial_schema.sql) has been applied

See `.cursor/plans/rds_dev_rollout_ci_cd_39a30e0b.plan.md` for rollout details."""

from __future__ import annotations

from helpers.api import ApiClient


def test_create_and_read_course_round_trips(api: ApiClient, course_factory):
    """POST /courses followed by GET /courses/{id} must succeed."""
    course = course_factory(description="rds-smoke")

    got = api.get_course(course.course_id)
    assert got.status_code == 200, (
        f"GET /courses/{course.course_id} expected 200, got "
        f"{got.status_code}: {got.text}"
    )
    body = got.json()
    assert body["id"] == course.course_id
    assert body["title"] == course.title
    assert body["description"] == "rds-smoke"
    assert body["status"] == "DRAFT"


def test_update_course_persists(api: ApiClient, course_factory):
    """PUT /courses/{id} must update metadata and be observable on the next GET."""
    course = course_factory(description="before")
    upd = api.update_course(
        course.course_id, title=course.title, description="after"
    )
    assert upd.status_code == 200, (
        f"PUT /courses/{course.course_id} expected 200, got "
        f"{upd.status_code}: {upd.text}"
    )

    got = api.get_course(course.course_id)
    assert got.status_code == 200
    assert got.json()["description"] == "after"


def test_lesson_create_under_course(
    api: ApiClient, course_factory, lesson_factory
):
    """Creating a lesson must succeed (FK: lessons.course_id -> courses.id)."""
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    listing = api.list_lessons(course.course_id)
    assert listing.status_code == 200
    lesson_ids = {item["id"] for item in listing.json()}
    assert lesson.lesson_id in lesson_ids, (
        f"lesson {lesson.lesson_id} not in GET /courses/{course.course_id}/lessons"
    )
