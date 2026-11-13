"""DSQL-6 S1: probe question-bank SELECT shapes on Aurora DSQL (D7).

When these tests pass, D7 is **compatible**: keep ``DISTINCT ON`` and
``ANY(%s::uuid[])`` in ``question_banks/rds_repo.py`` unchanged.

Skipped unless ``DSQL_ENDPOINT`` is set or ``StreamMyCourse-Dsql-prod`` resolves.
"""

from __future__ import annotations

import uuid

import pytest

from helpers.dsql_audit import admin_connect, execute_scalar, resolve_dsql_endpoint

_DISTINCT_ON_SQL = """
            SELECT DISTINCT ON (mq.module_id)
                mq.module_id,
                s.correct_count,
                s.total_count
            FROM module_quizzes mq
            INNER JOIN question_banks qb
              ON qb.id = mq.question_bank_id AND qb.course_id = %s
            INNER JOIN student_module_quiz_bindings b
              ON b.module_quiz_id = mq.id
             AND b.course_id = %s
             AND b.user_sub = %s
            INNER JOIN module_quiz_attempts a ON a.binding_id = b.id
            INNER JOIN module_quiz_attempt_submissions s ON s.attempt_id = a.id
            WHERE mq.course_id = %s
              AND mq.question_bank_id IS NOT NULL
              AND qb.status = 'PUBLISHED'
              AND mq.served_count_n IS NOT NULL
              AND mq.served_count_n >= 1
            ORDER BY mq.module_id, s.submitted_at DESC, s.attempt_id DESC
            """

_ANY_UUID_SQL = """
            SELECT COUNT(*)::int
            FROM questions
            WHERE course_id = %s AND id = ANY(%s::uuid[])
            """

_NIL_UUID = "00000000-0000-0000-0000-000000000000"
_PROBE_COURSE_ID = str(uuid.UUID(int=0))

pytestmark = pytest.mark.skipif(
    not resolve_dsql_endpoint(),
    reason="DSQL endpoint not configured (DSQL_ENDPOINT or StreamMyCourse-Dsql-prod)",
)


def test_dsql_distinct_on_latest_submission_score_shape_d7() -> None:
    """Live cluster probe for list_latest_submission_scores_for_course SQL shape."""
    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _DISTINCT_ON_SQL,
                (
                    _PROBE_COURSE_ID,
                    _PROBE_COURSE_ID,
                    _PROBE_COURSE_ID,
                    _PROBE_COURSE_ID,
                ),
            )
            rows = cur.fetchall()
    assert isinstance(rows, list)


def test_dsql_any_uuid_array_shape_d7() -> None:
    """Live cluster probe for list_student_bound_questions / grading ANY(uuid[]) shape."""
    with admin_connect() as conn:
        empty_count = execute_scalar(
            conn, _ANY_UUID_SQL, (_PROBE_COURSE_ID, [])
        )
        one_nil_count = execute_scalar(
            conn, _ANY_UUID_SQL, (_PROBE_COURSE_ID, [_NIL_UUID])
        )
    assert int(empty_count) == 0
    assert int(one_nil_count) == 0
