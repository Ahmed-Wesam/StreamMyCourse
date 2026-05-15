"""Unit tests for ``QuestionBankRdsRepository`` (mocked connection; no live Postgres)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest
from psycopg2 import errors as pg_errors

from services.common.errors import BadRequest, Conflict, NotFound
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


def _publish_cursor_success(*, draft_total: int = 2) -> FakeCursor:
    cur = FakeCursor()
    cur.rows_to_return = [
        ("bank-1", "DRAFT"),
        (draft_total,),
        (0,),
    ]
    cur.fetchall_batches = [
        [
            ("A", [{"key": "A", "text": "a"}]),
            ("B", [{"key": "B", "text": "b"}]),
        ][:draft_total]
    ]

    def on_execute(c: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "UPDATE questions" in sql and "SET status = 'PUBLISHED'" in sql:
            c.rowcount = draft_total
        elif "UPDATE question_banks" in sql:
            c.rowcount = 1
        elif "UPDATE module_quizzes" in sql:
            c.rowcount = 1

    cur._execute_impl = on_execute
    return cur


def test_publish_bank_transaction_commits_on_success() -> None:
    fake = FakeConn(cursor_obj=_publish_cursor_success())
    repo = QuestionBankRdsRepository(lambda: fake)

    repo.publish_bank_transaction(
        course_id="c1", bank_id="b1", module_id="m1", n=2
    )

    assert fake.committed == 1
    assert fake.rolled_back == 0
    sqls = " ".join(e[0] for e in fake.cursor_obj.executions)
    assert "FOR UPDATE" in sqls
    assert "UPDATE module_quizzes" in sqls


def test_publish_bank_transaction_conflict_when_bank_not_draft() -> None:
    cur = FakeCursor()
    cur.rows_to_return = [("bank-1", "PUBLISHED")]
    fake = FakeConn(cursor_obj=cur)
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(Conflict, match="not in DRAFT"):
        repo.publish_bank_transaction(
            course_id="c1", bank_id="b1", module_id="m1", n=1
        )
    assert fake.rolled_back == 1
    assert fake.committed == 0


def test_publish_bank_transaction_not_found_when_bank_missing() -> None:
    cur = FakeCursor()
    cur.rows_to_return = []
    fake = FakeConn(cursor_obj=cur)
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(NotFound, match="Question bank not found"):
        repo.publish_bank_transaction(
            course_id="c1", bank_id="b1", module_id="m1", n=1
        )
    assert fake.rolled_back == 1


def test_publish_bank_transaction_bad_request_no_module_quiz_link() -> None:
    cur = _publish_cursor_success(draft_total=1)
    cur.fetchall_batches = [[("A", [{"key": "A", "text": "a"}])]]

    def on_execute(c: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "UPDATE questions" in sql and "SET status = 'PUBLISHED'" in sql:
            c.rowcount = 1
        elif "UPDATE question_banks" in sql:
            c.rowcount = 1
        elif "UPDATE module_quizzes" in sql:
            c.rowcount = 0

    cur._execute_impl = on_execute
    fake = FakeConn(cursor_obj=cur)
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(BadRequest, match="No module quiz row"):
        repo.publish_bank_transaction(
            course_id="c1", bank_id="b1", module_id="m1", n=1
        )
    assert fake.rolled_back == 1


def test_publish_bank_transaction_rejects_invalid_correct_key() -> None:
    cur = FakeCursor()
    cur.rows_to_return = [("bank-1", "DRAFT"), (1,), (0,)]
    cur.fetchall_batches = [[("Z", [{"key": "A", "text": "a"}])]]
    fake = FakeConn(cursor_obj=cur)
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(BadRequest, match="correctOptionKey"):
        repo.publish_bank_transaction(
            course_id="c1", bank_id="b1", module_id="m1", n=1
        )
    assert fake.rolled_back == 1


def test_publish_bank_transaction_detects_draft_set_changed() -> None:
    cur = _publish_cursor_success(draft_total=2)

    def on_execute(c: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "UPDATE questions" in sql and "SET status = 'PUBLISHED'" in sql:
            c.rowcount = 1

    cur._execute_impl = on_execute
    fake = FakeConn(cursor_obj=cur)
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(BadRequest, match="draft question set changed"):
        repo.publish_bank_transaction(
            course_id="c1", bank_id="b1", module_id="m1", n=2
        )
    assert fake.rolled_back == 1


def _visibility_repo(rows: List[Tuple[Any, ...]]) -> tuple[QuestionBankRdsRepository, FakeConn]:
    fake = FakeConn()
    fake.cursor_obj.fetchall_batches = [rows]
    return QuestionBankRdsRepository(lambda: fake), fake


def test_list_module_quiz_visibility_for_course_empty_when_no_rows() -> None:
    repo, fake = _visibility_repo([])

    result = repo.list_module_quiz_visibility_for_course(course_id="c1")

    assert result == {}
    sql, params = fake.cursor_obj.executions[0]
    assert "module_quizzes" in sql
    assert "question_banks" in sql
    assert "c1" in params


def test_list_module_quiz_visibility_for_course_excludes_draft_bank() -> None:
    repo, _ = _visibility_repo([])

    result = repo.list_module_quiz_visibility_for_course(course_id="c1")

    assert result == {}


def test_list_module_quiz_visibility_for_course_includes_published_with_n() -> None:
    repo, fake = _visibility_repo([("m-published", 3)])

    result = repo.list_module_quiz_visibility_for_course(course_id="c1")

    assert result == {"m-published": {"servedCountN": 3}}
    sql, params = fake.cursor_obj.executions[0]
    assert "PUBLISHED" in sql
    assert "served_count_n" in sql
    assert params == ("c1", "c1")


def test_list_module_quiz_visibility_for_course_excludes_null_served_count_n() -> None:
    repo, _ = _visibility_repo([])

    result = repo.list_module_quiz_visibility_for_course(course_id="c1")

    assert result == {}


def test_list_module_quiz_visibility_for_course_filters_by_course_id() -> None:
    repo, fake = _visibility_repo([])

    repo.list_module_quiz_visibility_for_course(course_id="c-target")

    _, params = fake.cursor_obj.executions[0]
    assert params == ("c-target", "c-target")
