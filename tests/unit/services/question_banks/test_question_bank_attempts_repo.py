"""Unit tests for module-quiz attempt repo methods (QB-G slice 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest
from psycopg2 import errors as pg_errors

from services.common.errors import Conflict
from services.question_banks.rds_repo import QuestionBankRdsRepository

_UQ_IN_PROGRESS = "uq_module_quiz_attempts_one_in_progress"
_UQ_ATTEMPT_NUMBER = "module_quiz_attempts_binding_id_attempt_number_key"


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

    def __enter__(self) -> "FakeCursor":
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


def _attempt_row(
    *,
    attempt_id: str = "attempt-1",
    binding_id: str = "binding-1",
    attempt_number: int = 1,
    status: str = "in_progress",
    question_order: list[str] | None = None,
    choice_orders: dict[str, list[str]] | None = None,
    started_at: datetime | None = None,
    submitted_at: datetime | None = None,
) -> Tuple[Any, ...]:
    return (
        attempt_id,
        binding_id,
        attempt_number,
        status,
        question_order or ["q2", "q1"],
        choice_orders or {"q1": ["B", "A"], "q2": ["C", "A", "B"]},
        started_at or datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        submitted_at,
    )


def test_get_open_attempt_returns_none_when_missing() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = []
    repo = QuestionBankRdsRepository(lambda: fake)

    attempt = repo.get_open_attempt(binding_id="binding-1")

    assert attempt is None
    sql, params = fake.cursor_obj.executions[0]
    assert "module_quiz_attempts" in sql
    assert "status = 'in_progress'" in sql
    assert params == ("binding-1",)


def test_insert_attempt_with_shuffle_stores_and_get_open_attempt_loads() -> None:
    store: dict[str, Any] = {}

    def on_execute(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quiz_attempts" in sql:
            attempt_id = "attempt-uuid-1"
            store["attempt"] = {
                "id": attempt_id,
                "binding_id": params[0],
                "attempt_number": params[1],
                "status": "in_progress",
                "shuffled_question_order": params[2],
                "shuffled_choice_orders": params[3],
            }
            cur.rows_to_return = [
                _attempt_row(attempt_id=attempt_id, binding_id="binding-1"),
            ]

    fake = FakeConn()
    fake.cursor_obj._execute_impl = on_execute
    repo = QuestionBankRdsRepository(lambda: fake)

    inserted = repo.insert_attempt_with_shuffle(
        binding_id="binding-1",
        attempt_number=1,
        shuffled_question_order=["q2", "q1"],
        shuffled_choice_orders={"q1": ["B", "A"], "q2": ["C", "A", "B"]},
    )

    assert inserted.id == "attempt-uuid-1"
    assert inserted.startedAt
    assert fake.committed >= 1
    assert store["attempt"]["binding_id"] == "binding-1"
    assert store["attempt"]["attempt_number"] == 1

    load_fake = FakeConn()
    load_fake.cursor_obj.rows_to_return = [
        _attempt_row(attempt_id="attempt-uuid-1", binding_id="binding-1"),
    ]
    load_repo = QuestionBankRdsRepository(lambda: load_fake)

    loaded = load_repo.get_open_attempt(binding_id="binding-1")

    assert loaded is not None
    assert loaded.id == "attempt-uuid-1"
    assert loaded.bindingId == "binding-1"
    assert loaded.attemptNumber == 1
    assert loaded.status == "in_progress"
    assert loaded.shuffledQuestionOrder == ["q2", "q1"]
    assert loaded.shuffledChoiceOrders == {"q1": ["B", "A"], "q2": ["C", "A", "B"]}
    assert loaded.submittedAt is None


def test_get_latest_attempt_returns_highest_attempt_number() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        _attempt_row(
            attempt_id="attempt-3",
            attempt_number=3,
            status="submitted",
            submitted_at=datetime(2026, 5, 15, 13, 0, tzinfo=timezone.utc),
        ),
    ]
    repo = QuestionBankRdsRepository(lambda: fake)

    latest = repo.get_latest_attempt(binding_id="binding-1")

    assert latest is not None
    assert latest.attemptNumber == 3
    assert latest.status == "submitted"
    sql, params = fake.cursor_obj.executions[0]
    assert "ORDER BY attempt_number DESC" in sql
    assert "LIMIT 1" in sql
    assert params == ("binding-1",)


def test_insert_attempt_uses_incremented_attempt_number() -> None:
    """Caller passes attempt_number; repo tests document max+1 via get_latest_attempt."""
    fake_latest = FakeConn()
    fake_latest.cursor_obj.rows_to_return = [
        _attempt_row(attempt_id="attempt-2", attempt_number=2, status="submitted"),
    ]
    latest_repo = QuestionBankRdsRepository(lambda: fake_latest)
    latest = latest_repo.get_latest_attempt(binding_id="binding-1")
    assert latest is not None
    next_number = latest.attemptNumber + 1

    store: dict[str, Any] = {}

    def on_execute(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quiz_attempts" in sql:
            store["attempt_number"] = params[1]
            cur.rows_to_return = [
                _attempt_row(
                    attempt_id="attempt-uuid-3",
                    binding_id="binding-1",
                    attempt_number=next_number,
                ),
            ]

    fake_insert = FakeConn()
    fake_insert.cursor_obj._execute_impl = on_execute
    insert_repo = QuestionBankRdsRepository(lambda: fake_insert)

    inserted = insert_repo.insert_attempt_with_shuffle(
        binding_id="binding-1",
        attempt_number=next_number,
        shuffled_question_order=["q1"],
        shuffled_choice_orders={"q1": ["A"]},
    )

    assert inserted.id == "attempt-uuid-3"
    assert store["attempt_number"] == 3


def test_mark_attempt_submitted_updates_status() -> None:
    fake = FakeConn()
    fake.cursor_obj.rowcount = 1
    repo = QuestionBankRdsRepository(lambda: fake)

    submitted_at = datetime(2026, 5, 15, 14, 0, tzinfo=timezone.utc)
    repo.mark_attempt_submitted(
        attempt_id="attempt-1", submitted_at=submitted_at
    )

    sql, params = fake.cursor_obj.executions[0]
    assert "UPDATE module_quiz_attempts" in sql
    assert "status = 'submitted'" in sql
    assert "submitted_at" in sql
    assert params[0] == submitted_at
    assert params[1] == "attempt-1"
    assert fake.committed >= 1


def test_attempt_unique_violation_messages() -> None:
    from unittest.mock import MagicMock

    in_progress = MagicMock(spec=pg_errors.UniqueViolation)
    in_progress.diag.constraint_name = _UQ_IN_PROGRESS
    assert "in progress" in QuestionBankRdsRepository._attempt_unique_violation_message(
        in_progress
    )

    attempt_number = MagicMock(spec=pg_errors.UniqueViolation)
    attempt_number.diag.constraint_name = _UQ_ATTEMPT_NUMBER
    assert "attempt number" in QuestionBankRdsRepository._attempt_unique_violation_message(
        attempt_number
    )


def test_insert_attempt_maps_unique_violation_to_conflict() -> None:
    """Slice 3 will re-read open attempt on Conflict; repo must map UniqueViolation."""

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quiz_attempts" in sql:
            raise pg_errors.UniqueViolation("duplicate attempt")

    fake = FakeConn()
    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(Conflict, match="attempt"):
        repo.insert_attempt_with_shuffle(
            binding_id="binding-1",
            attempt_number=1,
            shuffled_question_order=["q1"],
            shuffled_choice_orders={"q1": ["A"]},
        )


def test_mark_attempt_submitted_then_get_open_attempt_returns_none() -> None:
    store: dict[str, Any] = {"status": "in_progress"}

    def on_execute(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "UPDATE module_quiz_attempts" in sql:
            store["status"] = "submitted"
            cur.rowcount = 1
        elif "status = 'in_progress'" in sql:
            if store["status"] == "submitted":
                cur.rows_to_return = []
            else:
                cur.rows_to_return = [
                    _attempt_row(attempt_id="attempt-1", binding_id="binding-1"),
                ]

    fake = FakeConn()
    fake.cursor_obj._execute_impl = on_execute
    fake.cursor_obj.rowcount = 1
    repo = QuestionBankRdsRepository(lambda: fake)

    repo.mark_attempt_submitted(attempt_id="attempt-1")
    assert repo.get_open_attempt(binding_id="binding-1") is None


def test_insert_binding_with_questions_and_initial_attempt_single_transaction() -> None:
    sql_log: list[str] = []

    def on_execute(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        sql_log.append(sql)
        if "INSERT INTO student_module_quiz_bindings" in sql:
            cur.rows_to_return = [("binding-uuid-1",)]
        elif "INSERT INTO student_module_quiz_binding_questions" in sql:
            pass
        elif "INSERT INTO module_quiz_attempts" in sql:
            assert params[0] == "binding-uuid-1"
            assert "in_progress" in sql
            assert len(params) == 3
            cur.rows_to_return = [("attempt-row",)]

    fake = FakeConn()
    fake.cursor_obj._execute_impl = on_execute
    repo = QuestionBankRdsRepository(lambda: fake)

    binding_id = repo.insert_binding_with_questions_and_initial_attempt(
        module_quiz_id="mq1",
        course_id="c1",
        user_sub="student-sub",
        question_ids=["q1", "q2"],
        shuffled_question_order=["q2", "q1"],
        shuffled_choice_orders={"q1": ["B", "A"], "q2": ["A", "B"]},
    )

    assert binding_id == "binding-uuid-1"
    assert fake.committed == 1
    assert fake.rolled_back == 0
    assert any("student_module_quiz_bindings" in s for s in sql_log)
    assert any("module_quiz_attempts" in s for s in sql_log)
