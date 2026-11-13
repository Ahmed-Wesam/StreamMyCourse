"""Catalog delete regression: modules, lessons, courses, purchase guard (DSQL-3 S5)."""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import billing_environment, decode_jwt_sub
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.factories import make_test_title
from helpers.module_contract import require_course_modules_list, require_lessons_include_module_fields

_PDF_BYTES = b"%PDF-1.4 minimal\n"
_PDF_SIZE = len(_PDF_BYTES)
_CONTENT_TYPE = "application/pdf"


def _is_dsql_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip() == "StreamMyCourse-Api-dsql"


def _create_ready_lesson_file(api: ApiClient, course_id: str, lesson_id: str) -> str:
    created = api.create_lesson_file(
        course_id,
        lesson_id,
        title=make_test_title("attach-file"),
        kind="resource",
        file_type="pdf",
        byte_size=_PDF_SIZE,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    file_id = str(body["fileId"])
    put = httpx.put(
        str(body["uploadUrl"]),
        content=_PDF_BYTES,
        headers={"Content-Type": _CONTENT_TYPE},
        timeout=30.0,
    )
    assert put.status_code == 200, put.text
    completed = api.complete_lesson_file_with_retry(course_id, lesson_id, file_id)
    assert completed.status_code == 200, completed.text
    return file_id


def _sql_counts(conn, course_id: str) -> tuple[int, int, int, int]:
    return (
        int(execute_scalar(conn, "SELECT COUNT(*) FROM app.courses WHERE id = %s", (course_id,)) or 0),
        int(
            execute_scalar(conn, "SELECT COUNT(*) FROM app.course_modules WHERE course_id = %s", (course_id,))
            or 0
        ),
        int(execute_scalar(conn, "SELECT COUNT(*) FROM app.lessons WHERE course_id = %s", (course_id,)) or 0),
        int(
            execute_scalar(conn, "SELECT COUNT(*) FROM app.lesson_files WHERE course_id = %s", (course_id,)) or 0
        ),
    )


def test_delete_module_removes_lesson_and_file(api: ApiClient, course_factory) -> None:
    course = course_factory(label="cat-del-mod")
    mods = require_course_modules_list(api.list_course_modules(course.course_id))
    default_id = min(mods, key=lambda m: int(m["order"]))["id"]

    extra = api.create_course_module(
        course.course_id, title=make_test_title("victim-mod"), description=""
    )
    assert extra.status_code == 201, extra.text
    victim_id = extra.json()["moduleId"]

    lr = api.create_lesson(
        course.course_id, title=make_test_title("mod-lesson"), module_id=victim_id
    )
    assert lr.status_code == 201, lr.text
    lesson_id = lr.json()["lessonId"]
    _create_ready_lesson_file(api, course.course_id, lesson_id)

    assert api.delete_course_module(course.course_id, victim_id).status_code == 200

    lessons = require_lessons_include_module_fields(api.list_lessons(course.course_id))
    assert lesson_id not in {x["id"] for x in lessons}

    remaining = require_course_modules_list(api.list_course_modules(course.course_id))
    assert len(remaining) == 1
    assert remaining[0]["id"] == default_id

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            _, _, lesson_n, file_n = _sql_counts(conn, course.course_id)
        assert lesson_n == 0
        assert file_n == 0

    assert api.delete_course(course.course_id).status_code == 200


def test_delete_lesson_removes_file_and_compacts_sibling(
    api: ApiClient, course_factory, lesson_factory
) -> None:
    course = course_factory(label="cat-del-lesson")
    a = lesson_factory(course.course_id, label="keep")
    b = lesson_factory(course.course_id, label="drop")
    assert (a.order, b.order) == (1, 2)
    _create_ready_lesson_file(api, course.course_id, b.lesson_id)

    assert api.delete_lesson(course.course_id, b.lesson_id).status_code == 200

    listed = require_lessons_include_module_fields(api.list_lessons(course.course_id))
    assert len(listed) == 1
    assert listed[0]["id"] == a.lesson_id
    assert listed[0]["order"] == 1

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            file_n = int(
                execute_scalar(
                    conn,
                    "SELECT COUNT(*) FROM app.lesson_files WHERE course_id = %s",
                    (course.course_id,),
                )
                or 0
            )
        assert file_n == 0

    assert api.delete_course(course.course_id).status_code == 200


def test_delete_course_removes_catalog_rows(api: ApiClient, course_factory, lesson_factory) -> None:
    course = course_factory(label="cat-del-course")
    lesson = lesson_factory(course.course_id, label="course-file")
    _create_ready_lesson_file(api, course.course_id, lesson.lesson_id)

    assert api.delete_course(course.course_id).status_code == 200
    assert api.get_course(course.course_id).status_code == 404

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            counts = _sql_counts(conn, course.course_id)
        assert counts == (0, 0, 0, 0)


def test_delete_last_module_still_bad_request(api: ApiClient, course_factory) -> None:
    course = course_factory(label="cat-del-last-mod")
    mods = require_course_modules_list(api.list_course_modules(course.course_id))
    assert len(mods) == 1
    only_id = mods[0]["id"]

    resp = api.delete_course_module(course.course_id, only_id)
    assert resp.status_code == 400, resp.text
    assert resp.json().get("code") == "bad_request"

    assert api.delete_course(course.course_id).status_code == 200


@pytest.mark.skipif(
    not _is_dsql_preview_stack(),
    reason="purchase-blocked course delete requires INTEGRATION_API_STACK=StreamMyCourse-Api-dsql",
)
def test_course_delete_blocked_when_purchase_row_exists(api: ApiClient, course_factory) -> None:
    course = course_factory(label="cat-del-purchase")
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    assert token, "INTEGRATION_COGNITO_JWT required"
    user_sub = decode_jwt_sub(token)
    purchase_id = str(uuid.uuid4())
    env = billing_environment()

    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.purchases (
                    id, user_sub, environment, product_type, course_id,
                    status, amount_minor, currency
                ) VALUES (%s, %s, %s, 'course', %s, 'paid', %s, 'JOD')
                """,
                (purchase_id, user_sub, env, course.course_id, 1000),
            )
        conn.commit()

    try:
        blocked = api.delete_course(course.course_id)
        assert blocked.status_code == 409, blocked.text
        assert blocked.json().get("code") == "conflict"
        assert api.get_course(course.course_id).status_code == 200
    finally:
        with admin_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM app.purchases WHERE id = %s", (purchase_id,))
            conn.commit()
        assert api.delete_course(course.course_id).status_code == 200
