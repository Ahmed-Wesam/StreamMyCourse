"""Unit tests for ``QuestionBankRdsRepository`` (mocked connection; no live Postgres)."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
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


class _UniqueViolationWithConstraint(pg_errors.UniqueViolation):
    """Test helper: psycopg2 ``diag`` is read-only; expose ``constraint_name`` for repo mapping."""

    def __init__(self, *, constraint_name: str, message: str = "duplicate") -> None:
        super().__init__(message)
        self._constraint_name = constraint_name

    @property
    def diag(self) -> SimpleNamespace:
        return SimpleNamespace(constraint_name=self._constraint_name)


def _unique_violation(*, constraint_name: str, message: str = "duplicate") -> pg_errors.UniqueViolation:
    return _UniqueViolationWithConstraint(constraint_name=constraint_name, message=message)


def test_insert_module_quiz_maps_unique_violation_to_conflict() -> None:
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quizzes" in sql:
            raise _unique_violation(constraint_name="module_quizzes_module_id_key")

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(Conflict, match="Module already has a quiz"):
        repo.insert_module_quiz(course_id="c1", module_id="m1")


def test_insert_module_quiz_maps_bank_unique_violation_to_conflict() -> None:
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO module_quizzes" in sql:
            raise _unique_violation(
                constraint_name="uq_module_quizzes_course_question_bank",
                message="duplicate bank",
            )

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(
        Conflict, match="Question bank is already linked to another module"
    ):
        repo.insert_module_quiz(
            course_id="c1", module_id="m2", question_bank_id="bank-1"
        )


def test_get_module_quiz_by_question_bank_id_returns_row() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        (
            "quiz-1",
            "c1",
            "m1",
            "bank-1",
            5,
            None,
            None,
        )
    ]
    repo = QuestionBankRdsRepository(lambda: fake)

    out = repo.get_module_quiz_by_question_bank_id(
        course_id="c1", question_bank_id="bank-1"
    )

    assert out is not None
    assert out.id == "quiz-1"
    assert out.courseId == "c1"
    assert out.moduleId == "m1"
    assert out.questionBankId == "bank-1"
    assert out.servedCountN == 5
    sql, params = fake.cursor_obj.executions[0]
    assert "question_bank_id = %s" in sql
    assert params == ("c1", "bank-1")


def test_get_module_quiz_by_question_bank_id_returns_none_when_missing() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = []
    repo = QuestionBankRdsRepository(lambda: fake)

    out = repo.get_module_quiz_by_question_bank_id(
        course_id="c1", question_bank_id="bank-missing"
    )

    assert out is None


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
        repo.insert_question_bank(course_id="deadbeef", name="Missing course")


def test_insert_question_bank_maps_check_violation_to_bad_request() -> None:
    fake = FakeConn()

    def boom(cur: FakeCursor, sql: str, params: Tuple[Any, ...]) -> None:
        if "INSERT INTO question_banks" in sql:
            raise pg_errors.CheckViolation("status check")

    fake.cursor_obj._execute_impl = boom
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(BadRequest, match="DRAFT"):
        repo.insert_question_bank(course_id="c1", name="Invalid", status="INVALID")


def test_insert_question_bank_success_returns_id() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [("bank-row-id",)]
    repo = QuestionBankRdsRepository(lambda: fake)

    bid = repo.insert_question_bank(course_id="c1", name="Final exam", status="DRAFT")

    assert bid == "bank-row-id"
    assert fake.committed >= 1
    insert_sql = [e[0] for e in fake.cursor_obj.executions if "INSERT INTO question_banks" in e[0]]
    assert insert_sql
    assert "course_id, name, status" in insert_sql[0]
    assert "VALUES (%s, %s, %s)" in insert_sql[0]
    assert fake.cursor_obj.executions[0][1] == ("c1", "Final exam", "DRAFT")


def test_get_bank_for_course_maps_name() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        ("bank-row-id", "c1", "Display name", "DRAFT", None, None)
    ]
    repo = QuestionBankRdsRepository(lambda: fake)

    bank = repo.get_bank_for_course(course_id="c1", bank_id="bank-row-id")

    assert bank is not None
    assert bank.name == "Display name"
    sql, params = fake.cursor_obj.executions[0]
    assert "name" in sql
    assert params == ("bank-row-id", "c1")


def test_list_question_banks_maps_nullable_name() -> None:
    fake = FakeConn()
    fake.cursor_obj.fetchall_batches = [
        [("bank-row-id", "c1", None, "DRAFT", None, None)]
    ]
    repo = QuestionBankRdsRepository(lambda: fake)

    banks = repo.list_question_banks_for_course(course_id="c1")

    assert len(banks) == 1
    assert banks[0].name is None
    sql, params = fake.cursor_obj.executions[0]
    assert "name" in sql
    assert params == ("c1",)


def test_update_question_bank_name_scoped_by_course_and_bank() -> None:
    fake = FakeConn()
    fake.cursor_obj.rowcount = 1
    repo = QuestionBankRdsRepository(lambda: fake)

    repo.update_question_bank_name(
        course_id="c1", bank_id="bank-row-id", name="Renamed bank"
    )

    assert fake.committed >= 1
    sql, params = fake.cursor_obj.executions[0]
    assert "UPDATE question_banks" in sql
    assert "name = %s" in sql
    assert "WHERE id = %s AND course_id = %s" in sql
    assert params == ("Renamed bank", "bank-row-id", "c1")


def test_update_question_bank_name_not_found_when_no_scoped_row() -> None:
    fake = FakeConn()
    fake.cursor_obj.rowcount = 0
    repo = QuestionBankRdsRepository(lambda: fake)

    with pytest.raises(NotFound, match="Question bank not found"):
        repo.update_question_bank_name(
            course_id="wrong-course", bank_id="bank-row-id", name="Nope"
        )


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


def test_list_latest_submission_scores_for_course_maps_rows() -> None:
    repo, fake = _visibility_repo([("m1", 2, 3)])

    result = repo.list_latest_submission_scores_for_course(
        course_id="c1", user_sub="student-sub"
    )

    assert result == {"m1": {"correctCount": 2, "totalCount": 3}}
    sql, params = fake.cursor_obj.executions[0]
    assert "module_quiz_attempt_submissions" in sql
    assert "DISTINCT ON (mq.module_id)" in sql
    assert params == ("c1", "c1", "student-sub", "c1")


def test_list_latest_submission_scores_for_course_empty_when_no_rows() -> None:
    repo, _ = _visibility_repo([])

    result = repo.list_latest_submission_scores_for_course(
        course_id="c1", user_sub="student-sub"
    )

    assert result == {}
