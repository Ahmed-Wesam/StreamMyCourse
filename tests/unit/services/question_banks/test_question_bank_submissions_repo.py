"""Unit tests for module-quiz submission repo methods (QB-H slice 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest
from psycopg2 import errors as pg_errors

from services.common.errors import Conflict, NotFound
from services.question_banks.rds_repo import QuestionBankRdsRepository


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    fetchall_batches: List[List[Tuple[Any, ...]]] = field(default_factory=list)
    rowcount: int = 1
    _execute_impl: Any = None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        if self._execute_impl is not None:
            self._execute_impl(self, sql, params)
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        if not self.fetchall_batches:
            return []
        return self.fetchall_batches.pop(0)

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        pass


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0
    autocommit: bool = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


def test_insert_submission_and_mark_submitted_runs_insert_then_update() -> None:
    fake = FakeConn()
    repo = QuestionBankRdsRepository(lambda: fake)

    submitted_at = datetime(2026, 5, 15, 15, 30, tzinfo=timezone.utc)
    repo.insert_submission_and_mark_submitted(
        attempt_id="attempt-1",
        answers_json={"q1": "A", "q2": "B"},
        correct_count=1,
        total_count=2,
        submitted_at=submitted_at,
    )

    assert len(fake.cursor_obj.executions) == 2
    sql_ins, params_ins = fake.cursor_obj.executions[0]
    sql_upd, params_upd = fake.cursor_obj.executions[1]
    assert "INSERT INTO module_quiz_attempt_submissions" in sql_ins
    assert params_ins[0] == "attempt-1"
    assert params_ins[2] == 1
    assert params_ins[3] == 2
    assert params_ins[4] == submitted_at

    assert "UPDATE module_quiz_attempts" in sql_upd
    assert "status = 'submitted'" in sql_upd
    assert params_upd == (submitted_at, "attempt-1")
    assert fake.committed == 1
    assert fake.rolled_back == 0


def test_insert_submission_and_mark_submitted_raises_not_found_when_attempt_missing() -> None:
    def on_execute(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "UPDATE module_quiz_attempts" in sql:
            cur.rowcount = 0

    fake = FakeConn()
    fake.cursor_obj._execute_impl = on_execute
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(NotFound, match="attempt"):
        repo.insert_submission_and_mark_submitted(
            attempt_id="missing",
            answers_json={"q1": "A"},
            correct_count=1,
            total_count=1,
        )

    assert fake.rolled_back >= 1
    assert fake.committed == 0


def test_get_latest_submission_for_binding_orders_by_submitted_at() -> None:
    t_newer = datetime(2026, 5, 16, 10, 0, tzinfo=timezone.utc)
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        (
            "attempt-2",
            2,
            ["q2", "q1"],
            {"q1": "B"},
            1,
            1,
            t_newer,
        ),
    ]
    repo = QuestionBankRdsRepository(lambda: fake)

    latest = repo.get_latest_submission_for_binding(binding_id="binding-1")

    assert latest is not None
    assert latest.attemptId == "attempt-2"
    assert latest.attemptNumber == 2
    assert latest.questionOrder == ["q2", "q1"]
    assert latest.answersJson == {"q1": "B"}
    assert latest.correctCount == 1
    assert latest.totalCount == 1
    sql, params = fake.cursor_obj.executions[0]
    assert "module_quiz_attempt_submissions" in sql
    assert "ORDER BY s.submitted_at DESC" in sql
    assert "s.attempt_id DESC" in sql
    assert params == ("binding-1",)


def test_get_latest_submission_returns_none_when_empty() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = []
    repo = QuestionBankRdsRepository(lambda: fake)

    assert repo.get_latest_submission_for_binding(binding_id="binding-x") is None


def test_get_attempt_with_binding_rows_loads_joined_context() -> None:
    started = datetime(2026, 5, 15, 9, 0, tzinfo=timezone.utc)
    submitted = datetime(2026, 5, 15, 9, 30, tzinfo=timezone.utc)
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        (
            "attempt-1",
            "binding-1",
            1,
            "submitted",
            ["q2", "q1"],
            {"q1": ["A", "B"]},
            started,
            submitted,
            "mq-1",
            "course-1",
            "user-sub-1",
            "module-9",
        ),
    ]
    repo = QuestionBankRdsRepository(lambda: fake)

    ctx = repo.get_attempt_with_binding_rows(attempt_id="attempt-1")

    assert ctx is not None
    assert ctx.attempt.id == "attempt-1"
    assert ctx.attempt.bindingId == "binding-1"
    assert ctx.attempt.attemptNumber == 1
    assert ctx.attempt.status == "submitted"
    assert ctx.attempt.shuffledQuestionOrder == ["q2", "q1"]
    assert ctx.attempt.shuffledChoiceOrders == {"q1": ["A", "B"]}
    assert ctx.moduleQuizId == "mq-1"
    assert ctx.courseId == "course-1"
    assert ctx.moduleId == "module-9"
    assert ctx.userSub == "user-sub-1"
    sql, params = fake.cursor_obj.executions[0]
    assert "FROM module_quiz_attempts a" in sql
    assert "student_module_quiz_bindings" in sql
    assert "module_quizzes" in sql
    assert params == ("attempt-1",)


def test_get_attempt_with_binding_rows_none() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = []
    repo = QuestionBankRdsRepository(lambda: fake)

    assert repo.get_attempt_with_binding_rows(attempt_id="nope") is None


def test_insert_submission_duplicate_maps_to_conflict() -> None:
    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quiz_attempt_submissions" in sql:
            raise pg_errors.UniqueViolation("duplicate submission")

    fake = FakeConn()
    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(Conflict, match="Submission already recorded"):
        repo.insert_submission_and_mark_submitted(
            attempt_id="attempt-1",
            answers_json={"q1": "A"},
            correct_count=1,
            total_count=1,
        )
