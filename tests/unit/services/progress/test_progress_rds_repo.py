"""Unit tests for `services.progress.rds_repo.LessonProgressRdsRepository`.

These tests use a hand-rolled mock connection/cursor so they run without a live
Postgres (psycopg2 is PostgreSQL-only; there is no SQLite mode).

Design contract enforced here:
  - SQL queries use parameterized statements (no f-strings for values)
  - ON CONFLICT UPDATE for upserts
  - Connection retry on OperationalError
  - Return LessonProgressRow dataclass instances
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest
import psycopg2


# ---------------------------------------------------------------------------
# Fake psycopg2 connection / cursor (reused pattern from test_rds_repos.py)
# ---------------------------------------------------------------------------


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    bulk_rows_to_return: Optional[List[Tuple[Any, ...]]] = None
    rowcount: int = 1
    closed: bool = False

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        if self.bulk_rows_to_return is not None:
            out = self.bulk_rows_to_return
            self.bulk_rows_to_return = None
            return out
        out = list(self.rows_to_return)
        self.rows_to_return.clear()
        return out

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0
    closed: bool = False

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_conn() -> FakeConn:
    return FakeConn()


@pytest.fixture
def fake_conn_factory(fake_conn: FakeConn):
    return lambda: fake_conn


# ---------------------------------------------------------------------------
# LessonProgressRdsRepository tests
# ---------------------------------------------------------------------------


class TestLessonProgressRdsRepository:
    @pytest.fixture
    def repo(self, fake_conn_factory):
        from services.progress.rds_repo import LessonProgressRdsRepository

        return LessonProgressRdsRepository(fake_conn_factory)

    def test_get_progress_for_course_returns_list_of_rows(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """Test get_progress_for_course returns list of LessonProgressRow."""
        now = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
        fake_conn.cursor_obj.bulk_rows_to_return = [
            ("user-1", "lesson-1", "course-1", True, now.isoformat(), 100, now.isoformat()),
            ("user-1", "lesson-2", "course-1", False, None, 30, now.isoformat()),
        ]

        result = repo.get_progress_for_course(user_sub="user-1", course_id="course-1")

        assert len(result) == 2
        assert result[0].user_sub == "user-1"
        assert result[0].lesson_id == "lesson-1"
        assert result[0].course_id == "course-1"
        assert result[0].completed is True
        assert result[0].completed_at == now.isoformat()
        assert result[0].last_position_sec == 100
        assert result[0].updated_at == now.isoformat()

        assert result[1].lesson_id == "lesson-2"
        assert result[1].completed is False
        assert result[1].completed_at is None
        assert result[1].last_position_sec == 30

        # Verify parameterized query
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "%s" in sql
        assert "user-1" in params
        assert "course-1" in params

    def test_get_progress_for_course_empty_returns_empty_list(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """Test get_progress_for_course returns empty list when no rows."""
        fake_conn.cursor_obj.bulk_rows_to_return = []

        result = repo.get_progress_for_course(user_sub="user-1", course_id="course-1")

        assert result == []

    def test_get_progress_for_lesson_returns_single_row(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """Test get_progress_for_lesson returns single LessonProgressRow."""
        now = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
        fake_conn.cursor_obj.rows_to_return.append(
            ("user-1", "lesson-1", "course-1", True, now.isoformat(), 100, now.isoformat())
        )

        result = repo.get_progress_for_lesson(user_sub="user-1", lesson_id="lesson-1")

        assert result is not None
        assert result.user_sub == "user-1"
        assert result.lesson_id == "lesson-1"
        assert result.course_id == "course-1"
        assert result.completed is True
        assert result.last_position_sec == 100

        # Verify parameterized query
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "%s" in sql
        assert "user-1" in params
        assert "lesson-1" in params

    def test_get_progress_for_lesson_returns_none_when_missing(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """Test get_progress_for_lesson returns None when no row."""
        # No rows staged -> fetchone returns None

        result = repo.get_progress_for_lesson(user_sub="user-1", lesson_id="missing")

        assert result is None
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "%s" in sql
        assert "user-1" in params
        assert "missing" in params

    def test_upsert_progress_uses_on_conflict_update(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """Test upsert_progress uses ON CONFLICT UPDATE pattern."""
        now = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
        # Single atomic query: INSERT...RETURNING (no separate get_progress call)
        fake_conn.cursor_obj.rows_to_return.append(
            ("user-1", "lesson-1", "course-1", True, now.isoformat(), 100, now.isoformat())
        )

        result = repo.upsert_progress(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=True,
            last_position_sec=100,
        )

        assert result.user_sub == "user-1"
        assert result.lesson_id == "lesson-1"
        assert result.completed is True
        assert result.last_position_sec == 100

        # Verify single atomic INSERT with ON CONFLICT (no TOCTOU race)
        assert len(fake_conn.cursor_obj.executions) == 1
        sql, params = fake_conn.cursor_obj.executions[0]
        assert "INSERT" in sql.upper()
        assert "ON CONFLICT" in sql.upper()
        assert "lesson_progress" in sql.lower()
        assert "CASE" in sql.upper()  # Atomic completed_at handling
        assert fake_conn.committed >= 1

    def test_upsert_progress_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """Test upsert_progress uses parameterized queries."""
        now = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
        # Single atomic query: INSERT...RETURNING (no separate get_progress call)
        fake_conn.cursor_obj.rows_to_return.append(
            ("user-1", "lesson-1", "course-1", False, None, 50, now.isoformat())
        )

        repo.upsert_progress(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=False,
            last_position_sec=50,
        )

        # Verify single atomic query
        assert len(fake_conn.cursor_obj.executions) == 1
        sql, params = fake_conn.cursor_obj.executions[0]
        assert "%s" in sql
        assert "user-1" in params
        assert "lesson-1" in params
        assert "course-1" in params
        assert False in params or 0 in params  # completed flag
        assert 50 in params  # position

    def test_execute_retries_once_on_operational_error(self) -> None:
        """Pin the reconnect+retry behavior in _execute (used by all queries)."""
        from services.progress.rds_repo import LessonProgressRdsRepository

        good = FakeConn()
        good.cursor_obj.bulk_rows_to_return = []
        attempt = {"n": 0}

        def factory() -> FakeConn:
            attempt["n"] += 1
            if attempt["n"] == 1:
                bad = FakeConn()

                def fail(sql: str, params: Sequence[Any] = ()) -> None:
                    raise psycopg2.OperationalError("connection lost")

                bad.cursor_obj.execute = fail  # type: ignore[assignment]
                return bad
            return good

        repo = LessonProgressRdsRepository(factory)
        assert repo.get_progress_for_course(user_sub="u", course_id="c") == []
        assert attempt["n"] == 2

    def test_execute_rolls_back_on_non_operational_error(self) -> None:
        from services.progress.rds_repo import LessonProgressRdsRepository

        conn = FakeConn()

        def fail(sql: str, params: Sequence[Any] = ()) -> None:
            raise ValueError("bad query")

        conn.cursor_obj.execute = fail  # type: ignore[assignment]
        repo = LessonProgressRdsRepository(lambda: conn)
        with pytest.raises(ValueError, match="bad query"):
            repo.get_progress_for_course(user_sub="u", course_id="c")
        assert conn.rolled_back >= 1

    def test_upsert_progress_sets_completed_at_when_completing(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """Test upsert_progress sets completed_at atomically when transitioning to completed=True.

        This test verifies the TOCTOU race condition fix: completed_at is determined
        by SQL CASE expression, not Python code, ensuring atomic decision-making.
        """
        now = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
        # Single atomic query: INSERT...RETURNING (no separate get_progress call)
        fake_conn.cursor_obj.rows_to_return.append(
            ("user-1", "lesson-1", "course-1", True, now.isoformat(), 100, now.isoformat())
        )

        result = repo.upsert_progress(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=True,
            last_position_sec=100,
        )

        assert result.completed is True
        assert result.completed_at is not None

        # Verify atomic SQL query with CASE expression for completed_at
        assert len(fake_conn.cursor_obj.executions) == 1
        sql = fake_conn.cursor_obj.executions[0][0]
        assert "completed_at" in sql.lower()
        assert "CASE" in sql.upper()
        assert "NOW()" in sql.upper()
