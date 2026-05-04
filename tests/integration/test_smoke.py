"""Smoke test that proves the harness wiring + per-test cleanup work.

If this module passes (and the safety net reports no leftovers), the rest of
the suite can rely on the same fixtures."""

from __future__ import annotations

from helpers.api import ApiClient
from helpers.factories import TEST_TITLE_PREFIX


def test_create_course_and_clean_up(api: ApiClient, course_factory):
    course = course_factory()
    assert course.course_id
    assert course.title.startswith(TEST_TITLE_PREFIX)

    # Course should be retrievable while the test is running.
    got = api.get_course(course.course_id)
    assert got.status_code == 200
    body = got.json()
    assert body["id"] == course.course_id
    assert body["title"] == course.title
    assert body["status"] == "DRAFT"

    # Cleanup happens via fixture finalizer; nothing else to assert here.


def test_health_list_courses(api: ApiClient):
    """Most basic health probe: GET /courses returns 200 and a JSON list."""
    resp = api.list_courses()
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
