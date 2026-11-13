"""DSQL-5 S2: purchase reservation user lock and price OCC (fake connection)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.purchases.repo import PurchaseRdsRepository

COURSE_ID = "b0000000-0000-4000-8000-000000000001"
USER_SUB = "student-sub"
PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    fetchone_results: List[Optional[Tuple[Any, ...]]] = field(default_factory=list)
    rowcount: int = 0

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None


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


def _sql_compact(sql: str) -> str:
    return " ".join(sql.lower().split())


def _repo(conn: FakeConn) -> PurchaseRdsRepository:
    return PurchaseRdsRepository(lambda: conn, deployment_environment="dev")


class TestReservePendingUserLock:
    def test_transaction_locks_user_then_stale_delete_then_fresh_select(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        conn.cursor_obj.fetchone_results = [None, None, None, (PURCHASE_ID,)]

        outcome = repo.reserve_pending_checkout(
            USER_SUB,
            product_type="course",
            course_id=COURSE_ID,
            amount_minor=50_000,
            currency="JOD",
            ttl_minutes=30,
        )

        assert outcome == ("reserved", PURCHASE_ID)
        kinds: List[str] = []
        for sql, _ in conn.cursor_obj.executions:
            compact = _sql_compact(sql)
            if "for update" in compact and "users" in compact:
                kinds.append("user_lock")
            elif "delete" in compact and "pending" in compact:
                kinds.append("stale_delete")
            elif "updated_at >" in compact or "updated_at <=" in compact:
                kinds.append("fresh_select")
            elif "status = 'paid'" in compact:
                kinds.append("paid_check")
            elif "insert" in compact:
                kinds.append("insert")
        assert kinds[:3] == ["user_lock", "stale_delete", "fresh_select"]
        assert kinds[-1] == "insert"
        assert "paid_check" in kinds
        assert conn.committed == 1

    def test_fresh_pending_returns_checkout_in_progress_without_insert(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        conn.cursor_obj.fetchone_results = [(1,)]

        outcome = repo.reserve_pending_checkout(
            USER_SUB,
            product_type="bundle",
            course_id=None,
            amount_minor=150_000,
            currency="JOD",
            ttl_minutes=30,
        )

        assert outcome == ("checkout_in_progress", None)
        assert not any("insert" in _sql_compact(sql) for sql, _ in conn.cursor_obj.executions)

    def test_paid_bundle_returns_already_owned_without_insert(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        conn.cursor_obj.fetchone_results = [None, (1,)]

        outcome = repo.reserve_pending_checkout(
            USER_SUB,
            product_type="bundle",
            course_id=None,
            amount_minor=150_000,
            currency="JOD",
            ttl_minutes=30,
        )

        assert outcome == ("already_owned", None)
        assert not any("insert" in _sql_compact(sql) for sql, _ in conn.cursor_obj.executions)

    def test_paid_course_returns_already_owned_without_insert(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        conn.cursor_obj.fetchone_results = [None, None, (1,)]

        outcome = repo.reserve_pending_checkout(
            USER_SUB,
            product_type="course",
            course_id=COURSE_ID,
            amount_minor=50_000,
            currency="JOD",
            ttl_minutes=30,
        )

        assert outcome == ("already_owned", None)
        assert not any("insert" in _sql_compact(sql) for sql, _ in conn.cursor_obj.executions)

    def test_retries_on_40001_and_inserts_once(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        conn.cursor_obj.fetchone_results = [None, None, (PURCHASE_ID,)]
        insert_runs = {"n": 0}
        txn_attempts = {"n": 0}
        original_execute = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            compact = _sql_compact(sql)
            if "insert" in compact:
                insert_runs["n"] += 1
            if "for update" in compact and "users" in compact:
                txn_attempts["n"] += 1
            if txn_attempts["n"] == 1 and "delete" in compact and "pending" in compact:
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err
            original_execute(sql, params)

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        outcome = repo.reserve_pending_checkout(
            USER_SUB,
            product_type="bundle",
            course_id=None,
            amount_minor=150_000,
            currency="JOD",
            ttl_minutes=30,
        )

        assert outcome == ("reserved", PURCHASE_ID)
        assert insert_runs["n"] == 1
        assert txn_attempts["n"] == 2
        assert conn.rolled_back == 1
        assert conn.committed == 1

    def test_reserve_body_does_not_commit_before_run_transaction(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        conn.cursor_obj.fetchone_results = [None, None, (PURCHASE_ID,)]
        commits_during_execute: List[int] = []
        original_execute = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            commits_during_execute.append(conn.committed)
            original_execute(sql, params)

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        repo.reserve_pending_checkout(
            USER_SUB,
            product_type="bundle",
            course_id=None,
            amount_minor=150_000,
            currency="JOD",
            ttl_minutes=30,
        )

        assert all(c == 0 for c in commits_during_execute)
        assert conn.committed == 1


class TestPriceUpdateOccRetry:
    def test_set_bundle_price_retries_on_40001(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        execute_calls = {"n": 0}
        original_execute = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            execute_calls["n"] += 1
            if execute_calls["n"] == 1:
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err
            original_execute(sql, params)

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        repo.set_bundle_price(150_000)

        assert execute_calls["n"] == 2
        assert conn.rolled_back == 1
        assert conn.committed == 1
        sql, params = conn.cursor_obj.executions[-1]
        assert "bundle_offers" in sql
        assert params == (150_000, "dev")

    def test_set_course_price_retries_on_40001(self) -> None:
        conn = FakeConn()
        repo = _repo(conn)
        conn.cursor_obj.rowcount = 1
        execute_calls = {"n": 0}
        original_execute = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            execute_calls["n"] += 1
            if execute_calls["n"] == 1:
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err
            original_execute(sql, params)

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        assert repo.set_course_price(COURSE_ID, 50_000) is True

        assert execute_calls["n"] == 2
        assert conn.rolled_back == 1
        assert conn.committed == 1
        sql, params = conn.cursor_obj.executions[-1]
        assert "price_amount_minor" in sql
        assert params == (50_000, COURSE_ID)
