"""DSQL-4 S3: lesson notes RDS transaction and note-cap guard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest

_USER = "student-1"
_COURSE_ID = "11111111-1111-1111-1111-111111111111"
_LESSON_ID = "22222222-2222-2222-2222-222222222222"


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    rowcount: int = 1

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        out = list(self.rows_to_return)
        self.rows_to_return.clear()
        return out


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0
    autocommit: bool = True
    autocommit_history: List[bool] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.autocommit_history.append(self.autocommit)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name == "autocommit" and getattr(self, "autocommit_history", None) is not None:
            self.autocommit_history.append(value)

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


@pytest.fixture
def fake_conn() -> FakeConn:
    return FakeConn()


@pytest.fixture
def repo(fake_conn: FakeConn):
    from services.lesson_notes.rds_repo import LessonNotesRdsRepository

    return LessonNotesRdsRepository(lambda: fake_conn)


def _insert_row() -> Tuple[Any, ...]:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return (
        "note-id-1",
        _USER,
        _COURSE_ID,
        _LESSON_ID,
        "body",
        10,
        now,
        now,
    )


def _sql_compact(sql: str) -> str:
    return " ".join(sql.lower().split())


class TestInsertNoteCapGuard:
    def test_insert_blocked_when_count_is_50(self, repo, fake_conn: FakeConn) -> None:
        from services.lesson_notes.errors import NoteLimitExceeded

        fake_conn.cursor_obj.rows_to_return = [(50,)]

        with pytest.raises(NoteLimitExceeded):
            repo.insert_note(
                user_sub=_USER,
                course_id=_COURSE_ID,
                lesson_id=_LESSON_ID,
                body="one more",
                timestamp_sec=None,
            )

        executions = fake_conn.cursor_obj.executions
        assert len(executions) == 2
        assert "for update" in _sql_compact(executions[0][0])
        assert "count" in _sql_compact(executions[1][0])
        assert fake_conn.committed == 0
        assert not any("insert into lesson_notes" in _sql_compact(s) for s, _ in executions)

    def test_insert_succeeds_when_count_is_49(self, repo, fake_conn: FakeConn) -> None:
        fake_conn.cursor_obj.rows_to_return = [(49,), _insert_row()]

        row = repo.insert_note(
            user_sub=_USER,
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            body="body",
            timestamp_sec=10,
        )

        assert row.body == "body"
        assert len(fake_conn.cursor_obj.executions) == 3
        assert "for update" in _sql_compact(fake_conn.cursor_obj.executions[0][0])
        assert "count" in _sql_compact(fake_conn.cursor_obj.executions[1][0])
        assert "insert into lesson_notes" in _sql_compact(fake_conn.cursor_obj.executions[2][0])
        assert fake_conn.committed == 1

    def test_insert_runs_for_update_then_count_then_insert(
        self, repo, fake_conn: FakeConn
    ) -> None:
        fake_conn.cursor_obj.rows_to_return = [(0,), _insert_row()]

        repo.insert_note(
            user_sub=_USER,
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            body="x",
            timestamp_sec=None,
        )

        kinds: List[str] = []
        for sql, _ in fake_conn.cursor_obj.executions:
            compact = _sql_compact(sql)
            if "for update" in compact and "users" in compact:
                kinds.append("for_update")
            elif "count" in compact:
                kinds.append("count")
            elif "insert into lesson_notes" in compact:
                kinds.append("insert")
        assert kinds == ["for_update", "count", "insert"]

    def test_insert_retries_whole_transaction_on_40001(
        self, repo, fake_conn: FakeConn
    ) -> None:
        fake_conn.cursor_obj.rows_to_return = [(49,), _insert_row()]
        count_runs = {"n": 0}
        execute_calls = {"n": 0}
        original_execute = fake_conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            execute_calls["n"] += 1
            compact = _sql_compact(sql)
            if "count" in compact:
                count_runs["n"] += 1
            if execute_calls["n"] == 2:
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err
            original_execute(sql, params)

        fake_conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        repo.insert_note(
            user_sub=_USER,
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            body="body",
            timestamp_sec=None,
        )

        assert count_runs["n"] == 2
        assert fake_conn.rolled_back == 1
        assert fake_conn.committed == 1

    def test_insert_body_does_not_commit_before_run_transaction(
        self, repo, fake_conn: FakeConn
    ) -> None:
        fake_conn.cursor_obj.rows_to_return = [(0,), _insert_row()]
        commits_during_execute: List[int] = []
        original_execute = fake_conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            commits_during_execute.append(fake_conn.committed)
            original_execute(sql, params)

        fake_conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        repo.insert_note(
            user_sub=_USER,
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            body="x",
            timestamp_sec=None,
        )

        assert commits_during_execute == [0, 0, 0]
        assert fake_conn.committed == 1


class TestUpdateDeleteOccRetry:
    def test_update_note_retries_on_40001_once(self, repo, fake_conn: FakeConn) -> None:
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        fake_conn.cursor_obj.rows_to_return = [
            (
                "note-id",
                _USER,
                _COURSE_ID,
                _LESSON_ID,
                "updated",
                None,
                now,
                now,
            ),
        ]
        calls = {"n": 0}
        original_execute = fake_conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err
            original_execute(sql, params)

        fake_conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        row = repo.update_note(
            note_id="note-id",
            user_sub=_USER,
            body="updated",
            timestamp_sec=None,
        )

        assert row.body == "updated"
        assert calls["n"] == 2
        assert fake_conn.rolled_back == 1
        assert fake_conn.committed == 1

    def test_delete_note_retries_on_40001_once(self, repo, fake_conn: FakeConn) -> None:
        calls = {"n": 0}
        original_execute = fake_conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            calls["n"] += 1
            if calls["n"] == 1:
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err
            original_execute(sql, params)
            fake_conn.cursor_obj.rowcount = 1

        fake_conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        ok = repo.delete_note(note_id="note-id", user_sub=_USER)

        assert ok is True
        assert calls["n"] == 2
        assert fake_conn.rolled_back == 1
        assert fake_conn.committed == 1
