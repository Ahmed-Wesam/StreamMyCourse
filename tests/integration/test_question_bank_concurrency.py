"""DSQL-6 S6: concurrent quiz start/submit against preview catalog + DSQL admin counts."""

from __future__ import annotations

import os
import threading
from typing import Any

import pytest

from helpers.api import ApiClient
from helpers.billing_access import decode_jwt_sub
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.module_contract import response_json_dict

from test_question_bank_start import _publish_bank_and_course, _question_ids_from_start
from test_question_bank_submit import _answers_all_first_choice

_PREVIEW_SKIP = "quiz concurrency integration runs only on StreamMyCourse-Api-dsql"


def _is_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip().endswith("Api-dsql")


pytestmark = pytest.mark.skipif(not _is_preview_stack(), reason=_PREVIEW_SKIP)


def _integration_student_sub() -> str:
    token = os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT_STUDENT not set")
    return decode_jwt_sub(token)


def _scalar(conn, sql: str, params: tuple[Any, ...]) -> int:
    return int(execute_scalar(conn, sql, params) or 0)


def _binding_count(conn, *, module_id: str, user_sub: str) -> int:
    return _scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM app.student_module_quiz_bindings b
        JOIN app.module_quizzes mq ON mq.id = b.module_quiz_id
        WHERE mq.module_id = %s AND b.user_sub = %s
        """,
        (module_id, user_sub),
    )


def _in_progress_attempt_count(conn, *, module_id: str, user_sub: str) -> int:
    return _scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM app.module_quiz_attempts a
        JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
        JOIN app.module_quizzes mq ON mq.id = b.module_quiz_id
        WHERE mq.module_id = %s AND b.user_sub = %s AND a.status = 'in_progress'
        """,
        (module_id, user_sub),
    )


def _submission_count(conn, *, module_id: str, user_sub: str) -> int:
    return _scalar(
        conn,
        """
        SELECT COUNT(*)
        FROM app.module_quiz_attempt_submissions s
        JOIN app.module_quiz_attempts a ON a.id = s.attempt_id
        JOIN app.student_module_quiz_bindings b ON b.id = a.binding_id
        JOIN app.module_quizzes mq ON mq.id = b.module_quiz_id
        WHERE mq.module_id = %s AND b.user_sub = %s
        """,
        (module_id, user_sub),
    )


def test_concurrent_start_one_binding_and_in_progress_attempt(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id, _ = _publish_bank_and_course(
        api_base_url,
        api,
        student_api,
        course_factory,
        lesson_factory,
        label="qb-concurrency-start",
        served_n=served_n,
    )
    user_sub = _integration_student_sub()
    results: list[Any] = []
    errors: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            resp = student_api.start_module_quiz(course_id, module_id)
            with lock:
                results.append(resp)
        except Exception as exc:
            with lock:
                errors.append(str(exc))

    try:
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=90.0)
        t2.join(timeout=90.0)
        assert not errors, errors
        assert len(results) == 2
        for resp in results:
            assert resp.status_code == 200, resp.text

        bodies = [response_json_dict(r) for r in results]
        ids_a = _question_ids_from_start(bodies[0])
        ids_b = _question_ids_from_start(bodies[1])
        assert ids_a == ids_b, (bodies[0], bodies[1])
        assert bodies[0].get("attemptId") == bodies[1].get("attemptId")

        with admin_connect() as conn:
            assert _binding_count(conn, module_id=module_id, user_sub=user_sub) == 1
            assert _in_progress_attempt_count(conn, module_id=module_id, user_sub=user_sub) == 1
    finally:
        api.delete_course(course_id)


def test_concurrent_submit_one_submission_row(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id, _ = _publish_bank_and_course(
        api_base_url,
        api,
        student_api,
        course_factory,
        lesson_factory,
        label="qb-concurrency-submit",
        served_n=served_n,
    )
    user_sub = _integration_student_sub()

    start = student_api.start_module_quiz(course_id, module_id)
    assert start.status_code == 200, start.text
    start_body = response_json_dict(start)
    attempt_id = str(start_body["attemptId"])
    payload = {"attemptId": attempt_id, "answers": _answers_all_first_choice(start_body)}

    results: list[Any] = []
    errors: list[str] = []
    lock = threading.Lock()

    def worker() -> None:
        try:
            resp = student_api.submit_module_quiz(course_id, module_id, payload)
            with lock:
                results.append(resp)
        except Exception as exc:
            with lock:
                errors.append(str(exc))

    try:
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=90.0)
        t2.join(timeout=90.0)
        assert not errors, errors
        assert len(results) == 2

        statuses = sorted(r.status_code for r in results)
        assert statuses == [200, 409], [r.status_code for r in results]
        winner = next(r for r in results if r.status_code == 200)
        loser = next(r for r in results if r.status_code == 409)
        assert response_json_dict(loser).get("code") == "conflict"
        assert response_json_dict(winner).get("attemptId") == attempt_id

        with admin_connect() as conn:
            assert _submission_count(conn, module_id=module_id, user_sub=user_sub) == 1
    finally:
        api.delete_course(course_id)
