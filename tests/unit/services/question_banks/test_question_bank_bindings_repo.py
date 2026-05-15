"""Unit tests for student module-quiz binding repo methods (QB-F slice 1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest
from psycopg2 import errors as pg_errors

from services.common.errors import Conflict
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


def test_list_published_question_ids_returns_only_published_for_bank_and_course() -> None:
    fake = FakeConn()
    fake.cursor_obj.fetchall_batches = [[("q-pub-1",), ("q-pub-2",)]]
    repo = QuestionBankRdsRepository(lambda: fake)

    ids = repo.list_published_question_ids(course_id="c1", bank_id="b1")

    assert ids == ["q-pub-1", "q-pub-2"]
    sql, params = fake.cursor_obj.executions[0]
    assert "FROM questions" in sql
    assert "status = 'PUBLISHED'" in sql
    assert params == ("c1", "b1")


def test_get_binding_for_student_returns_none_when_missing() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = []
    repo = QuestionBankRdsRepository(lambda: fake)

    binding = repo.get_binding_for_student(
        module_quiz_id="mq1", user_sub="student-sub"
    )

    assert binding is None
    sql, params = fake.cursor_obj.executions[0]
    assert "student_module_quiz_bindings" in sql
    assert params == ("mq1", "student-sub")


def test_insert_binding_with_questions_stores_and_loads_position_order() -> None:
    """Insert binding + rows; get_binding_for_student returns ids in position order."""
    store: dict[str, Any] = {}

    def on_execute(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO student_module_quiz_bindings" in sql:
            binding_id = "binding-uuid-1"
            store["binding"] = {
                "id": binding_id,
                "module_quiz_id": params[0],
                "course_id": params[1],
                "user_sub": params[2],
            }
            store["questions"] = []
            cur.rows_to_return = [(binding_id,)]
        elif "INSERT INTO student_module_quiz_binding_questions" in sql:
            store["questions"].append(
                {"binding_id": params[0], "position": params[1], "question_id": params[2]}
            )

    fake = FakeConn()
    fake.cursor_obj._execute_impl = on_execute
    repo = QuestionBankRdsRepository(lambda: fake)

    binding_id = repo.insert_binding_with_questions(
        module_quiz_id="mq1",
        course_id="c1",
        user_sub="student-sub",
        question_ids=["q3", "q1", "q2"],
    )

    assert binding_id == "binding-uuid-1"
    assert fake.committed >= 1
    insert_binding = [
        e for e in fake.cursor_obj.executions
        if "INSERT INTO student_module_quiz_bindings" in e[0]
    ]
    assert insert_binding
    assert len([e for e in fake.cursor_obj.executions if "binding_questions" in e[0]]) == 3

    # Simulate load: binding row then ordered question ids
    load_fake = FakeConn()
    load_fake.cursor_obj.rows_to_return = [
        ("binding-uuid-1", "mq1", "c1", "student-sub"),
    ]
    load_fake.cursor_obj.fetchall_batches = [[("q3",), ("q1",), ("q2",)]]
    load_repo = QuestionBankRdsRepository(lambda: load_fake)

    loaded = load_repo.get_binding_for_student(
        module_quiz_id="mq1", user_sub="student-sub"
    )

    assert loaded is not None
    assert loaded.id == "binding-uuid-1"
    assert loaded.moduleQuizId == "mq1"
    assert loaded.courseId == "c1"
    assert loaded.userSub == "student-sub"
    assert loaded.questionIds == ["q3", "q1", "q2"]
    load_sqls = [e[0] for e in load_fake.cursor_obj.executions]
    assert any("ORDER BY" in s and "position" in s for s in load_sqls)


def test_insert_binding_maps_unique_violation_to_conflict() -> None:
    """Slice 3 will re-read binding on Conflict; repo must map UniqueViolation."""
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO student_module_quiz_bindings" in sql:
            raise pg_errors.UniqueViolation("duplicate binding")

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(Conflict, match="binding"):
        repo.insert_binding_with_questions(
            module_quiz_id="mq1",
            course_id="c1",
            user_sub="student-sub",
            question_ids=["q1"],
        )
