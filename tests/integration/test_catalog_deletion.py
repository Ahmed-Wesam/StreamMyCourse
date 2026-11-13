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
    assert api.complete_lesson_file(course_id, lesson_id, file_id).status_code == 200
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


def _mcq_options() -> list[dict[str, str]]:
    return [{"key": "A", "text": "First"}, {"key": "B", "text": "Second"}]


def _setup_published_quiz_on_module(
    api: ApiClient,
    course_id: str,
    module_id: str,
    *,
    served_n: int = 2,
) -> str:
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    assert (
        api.create_module_quiz(course_id, module_id, question_bank_id=bank_id).status_code == 201
    )
    for i in range(served_n):
        dr = api.create_draft_question(
            course_id,
            bank_id,
            prompt_text=f"Del quiz Q{i + 1}?",
            options_json=_mcq_options(),
            correct_option_key="A",
        )
        assert dr.status_code == 201, dr.text
    pub = api.publish_question_bank(course_id, bank_id, n=served_n, module_id=module_id)
    assert pub.status_code == 200, pub.text
    return bank_id


def _quiz_row_counts_for_module(conn, module_id: str) -> tuple[int, int, int, int]:
    quiz_n = int(
        execute_scalar(conn, "SELECT COUNT(*) FROM app.module_quizzes WHERE module_id = %s", (module_id,))
        or 0
    )
    binding_n = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.student_module_quiz_bindings b
            JOIN app.module_quizzes mq ON mq.id = b.module_quiz_id
            WHERE mq.module_id = %s
            """,
            (module_id,),
        )
        or 0
    )
    attempt_n = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.module_quiz_attempts a
            JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
            JOIN app.module_quizzes mq ON mq.id = b.module_quiz_id
            WHERE mq.module_id = %s
            """,
            (module_id,),
        )
        or 0
    )
    submission_n = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.module_quiz_attempt_submissions s
            JOIN app.module_quiz_attempts a ON a.id = s.attempt_id
            JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
            JOIN app.module_quizzes mq ON mq.id = b.module_quiz_id
            WHERE mq.module_id = %s
            """,
            (module_id,),
        )
        or 0
    )
    return quiz_n, binding_n, attempt_n, submission_n


def _quiz_row_counts_for_course(conn, course_id: str) -> tuple[int, int, int, int, int, int, int]:
    banks = int(
        execute_scalar(conn, "SELECT COUNT(*) FROM app.question_banks WHERE course_id = %s", (course_id,))
        or 0
    )
    questions = int(
        execute_scalar(conn, "SELECT COUNT(*) FROM app.questions WHERE course_id = %s", (course_id,)) or 0
    )
    quizzes = int(
        execute_scalar(conn, "SELECT COUNT(*) FROM app.module_quizzes WHERE course_id = %s", (course_id,))
        or 0
    )
    bindings = int(
        execute_scalar(
            conn, "SELECT COUNT(*) FROM app.student_module_quiz_bindings WHERE course_id = %s", (course_id,)
        )
        or 0
    )
    attempts = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.module_quiz_attempts a
            JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
            WHERE b.course_id = %s
            """,
            (course_id,),
        )
        or 0
    )
    submissions = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.module_quiz_attempt_submissions s
            JOIN app.module_quiz_attempts a ON a.id = s.attempt_id
            JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
            WHERE b.course_id = %s
            """,
            (course_id,),
        )
        or 0
    )
    binding_questions = int(
        execute_scalar(
            conn,
            """
            SELECT COUNT(*)
            FROM app.student_module_quiz_binding_questions q
            JOIN app.student_module_quiz_bindings b ON b.id = q.binding_id
            WHERE b.course_id = %s
            """,
            (course_id,),
        )
        or 0
    )
    return banks, questions, quizzes, bindings, binding_questions, attempts, submissions


def test_delete_module_removes_quiz_rows_leaves_question_bank(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """DSQL-6 S6: module delete clears quiz + student rows; bank and questions stay."""
    from helpers.billing_access import ensure_student_subscription

    served_n = 2
    course = course_factory(label="cat-del-qb-mod")
    course_id = course.course_id

    extra = api.create_course_module(
        course_id, title=make_test_title("quiz-victim-mod"), description=""
    )
    assert extra.status_code == 201, extra.text
    victim_id = str(extra.json()["moduleId"])

    bank_id = _setup_published_quiz_on_module(api, course_id, victim_id, served_n=served_n)
    lesson = lesson_factory(course_id, label="cat-del-qb-lesson")
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course_id).status_code == 200
    ensure_student_subscription(api_base_url, student_api, course_id, lesson.lesson_id)

    start = student_api.start_module_quiz(course_id, victim_id)
    assert start.status_code == 200, start.text

    assert api.delete_course_module(course_id, victim_id).status_code == 200

    quiz_rows = [
        row
        for row in api.list_module_quizzes(course_id).json()
        if str(row.get("moduleId")) == victim_id
    ]
    assert quiz_rows == []
    assert student_api.start_module_quiz(course_id, victim_id).status_code == 404

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            assert _quiz_row_counts_for_module(conn, victim_id) == (0, 0, 0, 0)
            bank_n = int(
                execute_scalar(
                    conn,
                    "SELECT COUNT(*) FROM app.question_banks WHERE course_id = %s AND id = %s",
                    (course_id, bank_id),
                )
                or 0
            )
            question_n = int(
                execute_scalar(
                    conn,
                    "SELECT COUNT(*) FROM app.questions WHERE course_id = %s AND question_bank_id = %s",
                    (course_id, bank_id),
                )
                or 0
            )
        assert bank_n == 1
        assert question_n == served_n

    assert api.delete_course(course_id).status_code == 200

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            assert _quiz_row_counts_for_course(conn, course_id) == (0, 0, 0, 0, 0, 0, 0)
