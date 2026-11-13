"""DSQL-4 S6: lesson/module/course delete clears progress and notes."""

from __future__ import annotations

import os

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription
from helpers.dsql_audit import admin_connect
from helpers.dsql_preview_access import is_dsql_preview_api_stack
from helpers.factories import make_test_title
from helpers.learning_record_sql import (
    count_notes_for_course,
    count_notes_for_lesson,
    count_progress_for_course,
    count_progress_for_lesson,
)
from helpers.module_contract import require_course_modules_list


def _require_jwts() -> None:
    for name in ("INTEGRATION_COGNITO_JWT", "INTEGRATION_COGNITO_JWT_STUDENT"):
        if not os.environ.get(name, "").strip():
            raise SystemExit(f"Missing required JWT environment variable: {name}")


def _ready_lesson(api: ApiClient, course_id: str, lesson_id: str) -> None:
    assert api.get_upload_url(course_id=course_id, lesson_id=lesson_id).status_code == 200
    assert api.mark_video_ready(course_id, lesson_id).status_code == 200


def _write_progress_and_note(client: ApiClient, course_id: str, lesson_id: str, *, tag: str) -> None:
    prog = client.update_lesson_progress(course_id, lesson_id, position=30, duration=120)
    assert prog.status_code == 200, prog.text
    note = client.create_lesson_note(course_id, lesson_id, body=f"lr-del-{tag}")
    assert note.status_code == 201, note.text


def _two_module_course_with_lessons(
    api: ApiClient, course_factory, lesson_factory
) -> tuple[str, str, str, str]:
    """Return (course_id, sibling_lesson_id, victim_lesson_id, victim_module_id)."""
    course = course_factory(label="lr-del")
    mods = require_course_modules_list(api.list_course_modules(course.course_id))
    default_id = min(mods, key=lambda m: int(m["order"]))["id"]

    extra = api.create_course_module(course.course_id, title=make_test_title("lr-mod"), description="")
    assert extra.status_code == 201, extra.text
    victim_module_id = extra.json()["moduleId"]

    sibling = lesson_factory(course.course_id, label="lr-sibling")
    victim = api.create_lesson(
        course.course_id, title=make_test_title("lr-victim"), module_id=victim_module_id
    )
    assert victim.status_code == 201, victim.text
    victim_lesson_id = victim.json()["lessonId"]

    _ready_lesson(api, course.course_id, sibling.lesson_id)
    _ready_lesson(api, course.course_id, victim_lesson_id)
    assert api.publish_course(course.course_id).status_code == 200

    assert default_id  # default module is sibling's home
    return course.course_id, sibling.lesson_id, victim_lesson_id, victim_module_id


def test_lesson_delete_clears_progress_and_notes_for_owner_and_student(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    _require_jwts()
    course_id, sibling_id, victim_id, _ = _two_module_course_with_lessons(
        api, course_factory, lesson_factory
    )
    ensure_student_subscription(api_base_url, student_api, course_id, victim_id)

    _write_progress_and_note(api, course_id, victim_id, tag="owner")
    _write_progress_and_note(api, course_id, sibling_id, tag="owner-sib")
    _write_progress_and_note(student_api, course_id, victim_id, tag="student")
    _write_progress_and_note(student_api, course_id, sibling_id, tag="student-sib")

    assert api.delete_lesson(course_id, victim_id).status_code == 200

    for client in (api, student_api):
        missing = client.list_lesson_notes(course_id, victim_id)
        assert missing.status_code == 404, missing.text

    if is_dsql_preview_api_stack():
        with admin_connect() as conn:
            assert count_progress_for_lesson(conn, course_id=course_id, lesson_id=victim_id) == 0
            assert count_notes_for_lesson(conn, course_id=course_id, lesson_id=victim_id) == 0
            assert count_progress_for_lesson(conn, course_id=course_id, lesson_id=sibling_id) >= 2
            assert count_notes_for_lesson(conn, course_id=course_id, lesson_id=sibling_id) >= 2


def test_module_delete_clears_progress_and_notes_for_module_lessons(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    _require_jwts()
    course_id, sibling_id, victim_id, victim_module_id = _two_module_course_with_lessons(
        api, course_factory, lesson_factory
    )
    ensure_student_subscription(api_base_url, student_api, course_id, victim_id)

    _write_progress_and_note(api, course_id, victim_id, tag="mod-owner")
    _write_progress_and_note(student_api, course_id, victim_id, tag="mod-student")
    _write_progress_and_note(student_api, course_id, sibling_id, tag="mod-sibling")

    assert api.delete_course_module(course_id, victim_module_id).status_code == 200

    if is_dsql_preview_api_stack():
        with admin_connect() as conn:
            assert count_progress_for_lesson(conn, course_id=course_id, lesson_id=victim_id) == 0
            assert count_notes_for_lesson(conn, course_id=course_id, lesson_id=victim_id) == 0
            assert count_progress_for_lesson(conn, course_id=course_id, lesson_id=sibling_id) >= 1


def test_course_delete_clears_all_learning_records(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    _require_jwts()
    course_id, sibling_id, victim_id, _ = _two_module_course_with_lessons(
        api, course_factory, lesson_factory
    )
    ensure_student_subscription(api_base_url, student_api, course_id, victim_id)

    _write_progress_and_note(api, course_id, victim_id, tag="course-owner")
    _write_progress_and_note(student_api, course_id, sibling_id, tag="course-student")

    assert api.delete_course(course_id).status_code == 200
    assert api.get_course(course_id).status_code == 404

    if is_dsql_preview_api_stack():
        with admin_connect() as conn:
            assert count_progress_for_course(conn, course_id) == 0
            assert count_notes_for_course(conn, course_id) == 0


def test_delete_last_module_still_bad_request(api: ApiClient, course_factory) -> None:
    course = course_factory(label="lr-last-mod")
    mods = require_course_modules_list(api.list_course_modules(course.course_id))
    assert len(mods) == 1
    resp = api.delete_course_module(course.course_id, mods[0]["id"])
    assert resp.status_code == 400, resp.text
    assert resp.json().get("code") == "bad_request"
    assert api.delete_course(course.course_id).status_code == 200
