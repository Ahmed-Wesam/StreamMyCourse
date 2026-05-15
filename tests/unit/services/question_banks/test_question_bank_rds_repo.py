"""Unit tests for ``QuestionBankRdsRepository`` (mocked connection; no live Postgres)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest
from psycopg2 import errors as pg_errors

from services.common.errors import BadRequest, Conflict
from services.question_banks.rds_repo import QuestionBankRdsRepository


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
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


def test_insert_module_quiz_maps_unique_violation_to_conflict() -> None:
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quizzes" in sql:
            raise pg_errors.UniqueViolation("duplicate module")

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(Conflict, match="Module already has a quiz"):
        repo.insert_module_quiz(course_id="c1", module_id="m1")


def test_insert_module_quiz_maps_foreign_key_violation_to_bad_request() -> None:
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quizzes" in sql:
            raise pg_errors.ForeignKeyViolation("course mismatch")

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(BadRequest, match="course_modules"):
        repo.insert_module_quiz(
            course_id="c1", module_id="m1", question_bank_id="b-other"
        )


def test_insert_question_bank_maps_foreign_key_violation_to_bad_request() -> None:
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO question_banks" in sql:
            raise pg_errors.ForeignKeyViolation("no such course")

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(BadRequest, match="existing course"):
        repo.insert_question_bank(course_id="deadbeef")


def test_insert_question_bank_maps_check_violation_to_bad_request() -> None:
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO question_banks" in sql:
            raise pg_errors.CheckViolation("status check")

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(BadRequest, match="DRAFT"):
        repo.insert_question_bank(course_id="c1", status="INVALID")


def test_insert_question_bank_success_returns_id() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [("bank-row-id",)]
    repo = QuestionBankRdsRepository(lambda: fake)

    bid = repo.insert_question_bank(course_id="c1", status="DRAFT")

    assert bid == "bank-row-id"
    assert fake.committed >= 1
    insert_sql = [e[0] for e in fake.cursor_obj.executions if "INSERT INTO question_banks" in e[0]]
    assert insert_sql
    assert "VALUES (%s, %s)" in insert_sql[0]


def test_insert_module_quiz_success_returns_id() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [("quiz-row-id",)]
    repo = QuestionBankRdsRepository(lambda: fake)

    qid = repo.insert_module_quiz(course_id="c1", module_id="m1", question_bank_id=None)

    assert qid == "quiz-row-id"
    assert fake.committed >= 1
    insert_sql = [e[0] for e in fake.cursor_obj.executions if "INSERT INTO module_quizzes" in e[0]]
    assert insert_sql
    assert "VALUES (%s, %s, %s, %s)" in insert_sql[0]
