"""DSQL-4 S6: lesson notes author-only CRUD over HTTPS."""

from __future__ import annotations

import os

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.dsql_preview_access import is_dsql_preview_api_stack


def _require_jwts() -> None:
    for name in ("INTEGRATION_COGNITO_JWT", "INTEGRATION_COGNITO_JWT_STUDENT"):
        if not os.environ.get(name, "").strip():
            raise SystemExit(f"Missing required JWT environment variable: {name}")


def _published_lesson(api: ApiClient, course_factory, lesson_factory) -> tuple[str, str]:
    course = course_factory(label="notes-crud")
    lesson = lesson_factory(course.course_id, label="notes-lesson")
    assert api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id).status_code == 200
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200
    return course.course_id, lesson.lesson_id


def _note_count_by_id(conn, note_id: str) -> int:
    return int(
        execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.lesson_notes WHERE id = %s",
            (note_id,),
        )
        or 0
    )


def test_lesson_notes_owner_crud_other_caller_404_and_preview_sql(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Author CRUD; another principal cannot list or mutate the note; preview SQL empty after delete."""
    _require_jwts()
    course_id, lesson_id = _published_lesson(api, course_factory, lesson_factory)
    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

    created = student_api.create_lesson_note(
        course_id, lesson_id, body="integration note alpha", timestamp_sec=12
    )
    assert created.status_code == 201, created.text
    note_id = str(created.json()["note"]["id"])

    listed = student_api.list_lesson_notes(course_id, lesson_id)
    assert listed.status_code == 200, listed.text
    notes = listed.json().get("notes") or []
    assert any(n["id"] == note_id for n in notes)

    patched = student_api.update_lesson_note(
        course_id, lesson_id, note_id, body="integration note beta"
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["note"]["body"] == "integration note beta"

    other_list = api.list_lesson_notes(course_id, lesson_id)
    assert other_list.status_code == 200, other_list.text
    other_ids = {n["id"] for n in (other_list.json().get("notes") or [])}
    assert note_id not in other_ids

    bad_patch = api.update_lesson_note(course_id, lesson_id, note_id, body="hijack")
    assert bad_patch.status_code == 404, bad_patch.text

    bad_delete = api.delete_lesson_note(course_id, lesson_id, note_id)
    assert bad_delete.status_code == 404, bad_delete.text

    deleted = student_api.delete_lesson_note(course_id, lesson_id, note_id)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json().get("ok") is True

    after_list = student_api.list_lesson_notes(course_id, lesson_id)
    assert after_list.status_code == 200
    assert not any(n["id"] == note_id for n in (after_list.json().get("notes") or []))

    if is_dsql_preview_api_stack():
        with admin_connect() as conn:
            assert _note_count_by_id(conn, note_id) == 0
