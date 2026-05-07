"""Cross-teacher access control tests (IDOR / Broken Object-Level Authorization).

These tests verify that Teacher A cannot access or modify Teacher B's resources.
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import (
    EXPECTED_CATALOG_FORBIDDEN_403,
    require_course_modules_list,
    response_json_dict,
)


@pytest.mark.parametrize("operation_name,api_method,needs_lesson,needs_video", [
    ("update_course", "update_course", False, False),
    ("delete_course", "delete_course", False, False),
    ("publish_course", "publish_course", True, True),
    ("create_lesson", "create_lesson", False, False),
    ("update_lesson", "update_lesson", True, False),
    ("delete_lesson", "delete_lesson", True, False),
    ("mark_video_ready", "mark_video_ready", True, True),
    ("get_upload_url", "get_upload_url", True, False),
    ("create_course_module", "create_course_module", False, False),
    ("delete_course_module", "delete_course_module", False, False),
])
def test_teacher_cannot_access_other_teacher_resources(
    request: pytest.FixtureRequest,
    api: ApiClient,
    alt_api: ApiClient,
    alt_course_factory,
    operation_name: str,
    api_method: str,
    needs_lesson: bool,
    needs_video: bool,
):
    """Parameterized test ensuring Teacher A cannot access Teacher B's resources."""
    # Teacher B creates a course using the alt_course_factory
    course = alt_course_factory(label=f"[TEST] Teacher B Course for IDOR {operation_name} Test")
    course_id = course.course_id

    lesson_id = None

    # Setup additional resources if needed (lessons, etc.)
    if needs_lesson:
        alt_lesson_factory = request.getfixturevalue("alt_lesson_factory")
        lesson = alt_lesson_factory(course_id, label=f"[TEST] Teacher B Lesson for {operation_name}")
        lesson_id = lesson.lesson_id

        # Run any additional setup required via alt_api (e.g., get upload URL, mark video ready)
        if needs_video:
            setup_resp = alt_api.get_upload_url(course_id=course_id, lesson_id=lesson_id)
            assert setup_resp.status_code in (200, 204), f"Setup failed: {setup_resp.text}"
            ready_resp = alt_api.mark_video_ready(course_id, lesson_id)
            assert ready_resp.status_code in (200, 204), f"Setup failed: {ready_resp.text}"

    # Teacher A attempts operation on Teacher B's resources
    method = getattr(api, api_method)
    if api_method == "get_upload_url":
        resp = method(course_id=course_id, lesson_id=lesson_id)
    elif api_method == "create_lesson":
        resp = method(course_id, title="[TEST] Hijacked Lesson by Teacher A")
    elif api_method == "update_lesson":
        resp = method(course_id, lesson_id, title="[TEST] Hijacked Lesson by Teacher A")
    elif api_method in ["delete_lesson", "mark_video_ready"]:
        resp = method(course_id, lesson_id)
    elif api_method == "update_course":
        resp = method(course_id, title="[TEST] Hijacked by Teacher A", description="This should not be allowed")
    elif api_method == "publish_course":
        resp = method(course_id)
    elif api_method == "create_course_module":
        resp = method(course_id, title=make_test_title(f"idor-{operation_name}"), description="")
    elif api_method == "delete_course_module":
        mod_rows = require_course_modules_list(alt_api.list_course_modules(course_id))
        assert len(mod_rows) >= 1
        victim = mod_rows[0]["id"]
        resp = method(course_id, victim)
    else:
        resp = method(course_id)

    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")
