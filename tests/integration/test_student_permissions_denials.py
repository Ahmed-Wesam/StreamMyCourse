"""Negative role-based authorization tests — Broken Function-Level Authorization (OWASP API #5).

Tests that a student principal (JWT with role="student") cannot access instructor-only
routes. Expected rejection: 403 Forbidden with code "forbidden" for role-based rejection,
or 401 Unauthorized if not authenticated.
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.module_contract import (
    EXPECTED_ROLE_DENIAL_JSON,
    require_course_modules_list,
    response_json_dict,
)


@pytest.mark.parametrize(
    "endpoint_name,api_method,course_kwarg,lesson_kwarg,needs_module_id,extra_kwargs",
    [
        ("create_course", "create_course", None, None, False, {"title": "Student Unauthorized Course"}),
        (
            "update_course",
            "update_course",
            "course_id",
            None,
            False,
            {"title": "Student Modified Title", "description": "Student modified description"},
        ),
        ("delete_course", "delete_course", "course_id", None, False, {}),
        ("publish_course", "publish_course", "course_id", None, False, {}),
        ("create_lesson", "create_lesson", "course_id", None, False, {"title": "Student Unauthorized Lesson"}),
        ("update_lesson", "update_lesson", "course_id", "lesson_id", False, {"title": "Student Modified Lesson"}),
        ("delete_lesson", "delete_lesson", "course_id", "lesson_id", False, {}),
        ("mark_video_ready", "mark_video_ready", "course_id", "lesson_id", False, {}),
        (
            "get_upload_url",
            "get_upload_url",
            "course_id",
            "lesson_id",
            False,
            {"filename": "video.mp4", "content_type": "video/mp4"},
        ),
        ("thumbnail_ready", "thumbnail_ready", "course_id", None, False, {"thumbnail_key": "placeholder"}),
        (
            "create_course_module",
            "create_course_module",
            "course_id",
            None,
            False,
            {"title": "integration-test-student-module", "description": ""},
        ),
        ("delete_course_module", "delete_course_module", "course_id", None, True, {}),
    ],
)
def test_student_cannot_access_instructor_endpoints(
    request: pytest.FixtureRequest,
    student_api: ApiClient,
    api: ApiClient,
    endpoint_name: str,
    api_method: str,
    course_kwarg: str | None,
    lesson_kwarg: str | None,
    needs_module_id: bool,
    extra_kwargs: dict,
):
    """Parameterized test ensuring students are denied access to instructor-only endpoints."""
    # Setup: Create resources as instructor
    course_factory = request.getfixturevalue("course_factory")
    course = course_factory(label=f"Course For Student {endpoint_name} Denial Test")
    course_id = course.course_id

    lesson_factory = request.getfixturevalue("lesson_factory")
    lesson = lesson_factory(course_id, label=f"Lesson For Student {endpoint_name} Denial Test")
    lesson_id = lesson.lesson_id

    # Build kwargs for API call
    call_kwargs = dict(extra_kwargs)
    thumbnail_key = f"{course_id}/thumbnail/cover.jpg"

    # Inject course_id if the endpoint needs it
    if course_kwarg:
        call_kwargs[course_kwarg] = course_id

    # Inject lesson_id if the endpoint needs it
    if lesson_kwarg:
        call_kwargs[lesson_kwarg] = lesson_id

    # Special case for thumbnail_ready
    if api_method == "thumbnail_ready":
        call_kwargs["thumbnail_key"] = thumbnail_key

    if needs_module_id:
        mod_rows = require_course_modules_list(api.list_course_modules(course_id))
        call_kwargs["module_id"] = mod_rows[0]["id"]

    # Call the API method with student
    method = getattr(student_api, api_method)
    resp = method(**call_kwargs)

    assert resp.status_code in (401, 403), f"Expected 401 or 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    code = body.get("code")
    if code not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={resp.status_code} body={body!r}")
