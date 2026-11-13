"""Unit tests for DSQL FK orphan audit SQL (plans/dsql-ws1-foundation.md S7)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_SCRIPTS))

from dsql_fk_pairs import (  # noqa: E402
    DSQL_FOREIGN_KEY_EDGES,
    build_orphan_count_sql,
    pairs_matching_schema,
)
from dsql_orphan_audit import fk_orphan_counts, run_audit  # noqa: E402

_SCHEMA = _REPO / "infrastructure" / "database" / "dsql" / "0001_schema.sql"

# §6.1 child→parent pairs declared as REFERENCES in 0001_schema.sql
# (assignment_submissions.user_sub has no FK on RDS/DSQL — excluded intentionally).
PAIRS_6_1_IN_SCHEMA = frozenset(
    {
        ("course_modules", "courses"),
        ("lessons", "courses"),
        ("lessons", "course_modules"),
        ("lesson_files", "lessons"),
        ("question_banks", "courses"),
        ("questions", "courses"),
        ("questions", "question_banks"),
        ("module_quizzes", "courses"),
        ("module_quizzes", "course_modules"),
        ("module_quizzes", "question_banks"),
        ("student_module_quiz_bindings", "module_quizzes"),
        ("student_module_quiz_bindings", "courses"),
        ("student_module_quiz_binding_questions", "student_module_quiz_bindings"),
        ("student_module_quiz_binding_questions", "questions"),
        ("module_quiz_attempts", "student_module_quiz_bindings"),
        ("module_quiz_attempt_submissions", "module_quiz_attempts"),
        ("assignments", "courses"),
        ("assignments", "course_modules"),
        ("assignment_criteria", "assignments"),
        ("assignment_submissions", "assignments"),
        ("assignment_submission_files", "assignment_submissions"),
        ("assignment_submission_files", "assignments"),
        ("assignment_grades", "assignment_submissions"),
        ("assignment_grades", "assignments"),
        ("assignment_grade_scores", "assignment_grades"),
        ("assignment_grade_scores", "assignment_criteria"),
        ("lesson_progress", "users"),
        ("lesson_progress", "lessons"),
        ("lesson_progress", "courses"),
        ("lesson_notes", "users"),
        ("lesson_notes", "lessons"),
        ("learning_activity_days", "users"),
        ("research_team_required_courses", "courses"),
        ("purchases", "users"),
        ("purchases", "courses"),
        ("certificates", "courses"),
    }
)


def test_fk_list_matches_6_1_schema_pairs() -> None:
    assert pairs_matching_schema() == PAIRS_6_1_IN_SCHEMA


def test_fk_list_count_matches_references_clause_count_in_schema() -> None:
    sql = _SCHEMA.read_text(encoding="utf-8")
    ref_clauses = len(re.findall(r"REFERENCES\s+app\.\w+", sql, flags=re.IGNORECASE))
    # `app.enrollments` is dropped by DSQL migration 0003; 0001 still declares its FKs.
    enrollments_refs = 2
    assert len(DSQL_FOREIGN_KEY_EDGES) == ref_clauses - enrollments_refs


@pytest.mark.parametrize("edge", DSQL_FOREIGN_KEY_EDGES, ids=lambda e: e.label)
def test_orphan_sql_is_left_join_is_null(edge: Any) -> None:
    sql = build_orphan_count_sql(edge)
    lowered = sql.lower()
    assert "left join" in lowered
    assert " is null" in lowered
    assert f"app.{edge.child_table}" in sql
    assert f"app.{edge.parent_table}" in sql


def test_orphan_sql_never_uses_deleting_status() -> None:
    for edge in DSQL_FOREIGN_KEY_EDGES:
        sql = build_orphan_count_sql(edge)
        assert "deleting" not in sql.lower()
        assert "courses.status" not in sql.lower()


def test_fk_orphan_counts_reports_nonzero(fake_cursor: MagicMock) -> None:
    counts = {DSQL_FOREIGN_KEY_EDGES[0].label: 3}
    call_idx = {"n": 0}

    def execute_side_effect(sql: str) -> None:
        idx = call_idx["n"]
        call_idx["n"] += 1
        cnt = 3 if idx == 0 else 0
        fake_cursor.fetchone.return_value = (cnt,)

    fake_cursor.execute.side_effect = execute_side_effect
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = fake_cursor
    conn.cursor.return_value.__exit__.return_value = False

    findings = fk_orphan_counts(conn)
    assert len(findings) == 1
    assert findings[0][1] == 3


@pytest.fixture
def fake_cursor() -> MagicMock:
    cur = MagicMock()
    cur.fetchone.return_value = (0,)
    return cur


def test_run_audit_exit_code_zero_when_clean(fake_cursor: MagicMock) -> None:
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = fake_cursor
    conn.cursor.return_value.__exit__.return_value = False
    assert run_audit(conn) == 0


def test_run_audit_exit_code_nonzero_when_findings(fake_cursor: MagicMock) -> None:
    fake_cursor.fetchone.return_value = (1,)
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value = fake_cursor
    conn.cursor.return_value.__exit__.return_value = False
    assert run_audit(conn) == 1
