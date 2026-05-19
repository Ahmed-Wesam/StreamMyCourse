"""Concurrent incomplete reservation returns checkout_in_progress (not 503)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.subscription.repo import SubscriptionRdsRepository

try:
    import psycopg2
    from psycopg2 import errors as psycopg2_errors
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]
    psycopg2_errors = None  # type: ignore[assignment]


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    fetchone_results: List[Optional[Tuple[Any, ...]]] = field(default_factory=list)
    rowcount: int = 0
    rowcount_per_execute: List[int] = field(default_factory=list)
    insert_raises_unique: bool = False

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))
        if self.rowcount_per_execute and sql.lstrip().upper().startswith("UPDATE"):
            self.rowcount = self.rowcount_per_execute.pop(0)
        if self.insert_raises_unique and "INSERT" in sql.upper():
            if psycopg2_errors is None:
                raise RuntimeError("unique violation simulation requires psycopg2")
            raise psycopg2_errors.UniqueViolation("duplicate key")

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    autocommit: bool = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _repo(conn: FakeConn) -> SubscriptionRdsRepository:
    return SubscriptionRdsRepository(lambda: conn, deployment_environment="dev")


class TestReserveIncompleteRace:
    def test_unique_violation_on_insert_returns_checkout_in_progress(self) -> None:
        if psycopg2 is None:
            pytest.skip("psycopg2 not installed")
        conn = FakeConn()
        conn.cursor_obj.fetchone_results = [None]  # fresh incomplete check
        conn.cursor_obj.rowcount_per_execute = [0, 0]  # incomplete + lapsed miss
        conn.cursor_obj.insert_raises_unique = True
        repo = _repo(conn)

        outcome = repo.reserve_incomplete_checkout(
            "student-sub",
            "a0000000-0000-4000-8000-000000000011",
            ttl_minutes=30,
        )

        assert outcome == "checkout_in_progress"

    def test_reserve_runs_delete_fresh_and_upsert_in_one_flow(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.fetchone_results = [None]
        conn.cursor_obj.rowcount_per_execute = [0, 0, 0]  # incomplete, lapsed, insert path
        repo = _repo(conn)

        outcome = repo.reserve_incomplete_checkout(
            "student-sub",
            "a0000000-0000-4000-8000-000000000011",
            ttl_minutes=30,
        )

        assert outcome == "reserved"
        joined = "\n".join(sql for sql, _ in conn.cursor_obj.executions)
        assert "DELETE" in joined.upper()
        assert "incomplete" in joined.lower()
        assert "INSERT" in joined.upper()

    def test_lapsed_active_row_reopened_without_insert(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.fetchone_results = [None]
        conn.cursor_obj.rowcount_per_execute = [0, 1]  # incomplete miss; lapsed hit
        repo = _repo(conn)

        outcome = repo.reserve_incomplete_checkout(
            "student-sub",
            "a0000000-0000-4000-8000-000000000011",
            ttl_minutes=30,
        )

        assert outcome == "reserved"
        joined = "\n".join(sql for sql, _ in conn.cursor_obj.executions)
        assert "active" in joined or "past_due" in joined
        assert "INSERT" not in joined.upper()
