"""Unit tests for AssignmentsRdsRepository transaction and OCC behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.assignments.rds_repo import AssignmentsRdsRepository
from services.common.errors import Conflict


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


def _sql_compact(sql: str) -> str:
    return " ".join(sql.lower().split())


def test_replace_criteria_locks_assignment_without_body_commit() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [("a1",)]
    commits_during: list[int] = []
    original = fake.cursor_obj.execute

    def execute(sql: str, params: Sequence[Any] = ()) -> None:
        commits_during.append(fake.committed)
        original(sql, params)
        if "INSERT INTO assignment_criteria" in sql:
            fake.cursor_obj.rows_to_return.append(
                ("c1", "a1", "Label", 10, 0),
            )

    fake.cursor_obj.execute = execute  # type: ignore[method-assign]
    repo = AssignmentsRdsRepository(lambda: fake)
    out = repo.replace_criteria(
        assignment_id="a1", criteria=[("c1", "Label", 10)]
    )
    assert len(out) == 1
    assert commits_during == [0] * len(commits_during)
    assert fake.committed == 1
    assert any("for update" in _sql_compact(s) for s, _ in fake.cursor_obj.executions)


def test_replace_criteria_retries_40001_once() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        ("a1",),
        ("a1",),
        ("c1", "a1", "L", 5, 0),
    ]
    deletes = {"n": 0}
    original = fake.cursor_obj.execute

    def execute(sql: str, params: Sequence[Any] = ()) -> None:
        original(sql, params)
        if "DELETE FROM assignment_criteria" in sql:
            deletes["n"] += 1
            if deletes["n"] == 1:
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err

    fake.cursor_obj.execute = execute  # type: ignore[method-assign]
    repo = AssignmentsRdsRepository(lambda: fake)
    repo.replace_criteria(assignment_id="a1", criteria=[("c1", "L", 5)])
    assert deletes["n"] == 2
    assert fake.rolled_back == 1
    assert fake.committed == 1


def test_insert_grade_conflict_when_submission_already_graded() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [("graded",)]
    repo = AssignmentsRdsRepository(lambda: fake)
    with pytest.raises(Conflict, match="immutable"):
        repo.insert_grade(
            submission_id="s1",
            assignment_id="a1",
            course_id="c1",
            score_percent=80,
            pass_percent=70,
            passed=True,
            feedback="",
            graded_by="t1",
            scores=[("c1", 10)],
        )
    assert not any(
        "INSERT INTO assignment_grades" in s for s, _ in fake.cursor_obj.executions
    )


def test_insert_grade_updates_status_in_same_transaction() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        ("submitted",),
        (
            "g1",
            "s1",
            "a1",
            "c1",
            80,
            70,
            True,
            "ok",
            "t1",
            None,
        ),
    ]
    repo = AssignmentsRdsRepository(lambda: fake)
    repo.insert_grade(
        submission_id="s1",
        assignment_id="a1",
        course_id="c1",
        score_percent=80,
        pass_percent=70,
        passed=True,
        feedback="ok",
        graded_by="t1",
        scores=[("c1", 10)],
    )
    sqls = [_sql_compact(s) for s, _ in fake.cursor_obj.executions]
    assert any("for update" in s for s in sqls)
    assert any(
        "update assignment_submissions" in s and "graded" in s for s in sqls
    )
    assert fake.committed == 1


def test_insert_submission_sql_contains_draft_on_conflict() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        ("s1", "a1", "c1", "u1", "draft", "", None, None, None),
    ]
    repo = AssignmentsRdsRepository(lambda: fake)
    repo.insert_submission(
        course_id="c1", assignment_id="a1", user_sub="u1", status="draft"
    )
    insert_sql = fake.cursor_obj.executions[0][0]
    lowered = insert_sql.lower()
    assert "on conflict" in lowered
    assert "do nothing" in lowered
    assert "status = 'draft'" in lowered


def test_insert_assignment_retries_40001() -> None:
    fake = FakeConn()
    fake.cursor_obj.rows_to_return = [
        (
            "a1",
            "c1",
            "m1",
            "T",
            "draft",
            70,
            False,
            "plain",
            "",
            "",
            "",
            False,
            "plain",
            "",
            "",
            "",
            False,
            None,
            None,
        ),
        (
            "a1",
            "c1",
            "m1",
            "T",
            "draft",
            70,
            False,
            "plain",
            "",
            "",
            "",
            False,
            "plain",
            "",
            "",
            "",
            False,
            None,
            None,
        ),
    ]
    calls = {"n": 0}
    original = fake.cursor_obj.execute

    def execute(sql: str, params: Sequence[Any] = ()) -> None:
        calls["n"] += 1
        original(sql, params)
        if "INSERT INTO assignments" in sql and calls["n"] == 1:
            err = Exception("serialization failure")
            err.pgcode = "40001"  # type: ignore[attr-defined]
            raise err

    fake.cursor_obj.execute = execute  # type: ignore[method-assign]
    repo = AssignmentsRdsRepository(lambda: fake)
    row = repo.insert_assignment(
        course_id="c1",
        module_id="m1",
        title="T",
        pass_percent=70,
        counts_toward_certificate=False,
    )
    assert row.id == "a1"
    assert fake.rolled_back == 1
    assert fake.committed == 1
