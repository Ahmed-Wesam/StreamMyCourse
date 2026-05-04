"""RDS PostgreSQL path smoke tests.

These tests only run when `USE_RDS=true` in the environment -- they assert that
the deployed API can round-trip writes and reads when the Lambda is wired to
RDS instead of DynamoDB. The rest of the integration suite also exercises the
RDS path transparently when the flag is on; this module adds a dedicated,
self-describing smoke so CI can flag RDS-specific breakage quickly.

The tests assume:
- `USE_RDS` env var is truthy (set by verify-dev-rds / verify-prod-rds via verify-rds-reusable.yml)
- `INTEG_API_BASE_URL` points at the API deployed with `USE_RDS=true`
- The PostgreSQL schema (001_initial_schema.sql) has been applied

See `.cursor/plans/rds_dev_rollout_ci_cd_39a30e0b.plan.md` for rollout details."""

from __future__ import annotations

import os

import pytest

from helpers.api import ApiClient


def _use_rds_enabled() -> bool:
    value = os.environ.get("USE_RDS", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


pytestmark = pytest.mark.skipif(
    not _use_rds_enabled(),
    reason="USE_RDS not enabled; skipping RDS-specific smoke tests",
)


def test_create_and_read_course_round_trips_via_rds(api: ApiClient, course_factory):
    """POST /courses followed by GET /courses/{id} must succeed against RDS.

    Failure here means either the Lambda is not actually wired to RDS, the
    schema is missing/stale, or the VPC/SG/Secrets Manager plumbing is broken.
    """
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


def test_update_course_persists_via_rds(api: ApiClient, course_factory):
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


def test_lesson_create_under_course_via_rds(
    api: ApiClient, course_factory, lesson_factory
):
    """Creating a lesson must succeed (FK: lessons.course_id -> courses.id) on RDS."""
    course = course_factory()
    lesson = lesson_factory(course.course_id)

    listing = api.list_lessons(course.course_id)
    assert listing.status_code == 200
    lesson_ids = {item["id"] for item in listing.json()}
    assert lesson.lesson_id in lesson_ids, (
        f"lesson {lesson.lesson_id} not in GET /courses/{course.course_id}/lessons"
    )
