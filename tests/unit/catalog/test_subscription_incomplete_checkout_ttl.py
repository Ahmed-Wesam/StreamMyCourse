"""Fresh vs stale incomplete checkout reservations (review fix)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.subscription.checkout_service import (
    INCOMPLETE_CHECKOUT_TTL_MINUTES,
    BillingCheckoutService,
)
from services.subscription.repo import SubscriptionRdsRepository

DEV_PLAN_ID = "a0000000-0000-4000-8000-000000000011"


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
    autocommit: bool = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _service() -> tuple[BillingCheckoutService, FakeConn]:
    conn = FakeConn()
    repo = SubscriptionRdsRepository(lambda: conn, deployment_environment="dev")
    return BillingCheckoutService(repo), conn


class TestIncompleteCheckoutTtl:
    def test_stale_incomplete_cleared_before_retry(self) -> None:
        svc, conn = _service()
        conn.cursor_obj.fetchone_results = [
            None,  # reactivation
            None,  # active/past_due block
            (50000, "JOD", "monthly_all_access"),  # plan
            None,  # fresh incomplete inside reserve txn
        ]
        conn.cursor_obj.rowcount = 0

        result = svc.run_billing_checkout_precheck("student-sub", DEV_PLAN_ID)

        assert result["blockReason"] is None
        joined = "\n".join(sql for sql, _ in conn.cursor_obj.executions)
        assert "DELETE" in joined.upper()
        assert str(INCOMPLETE_CHECKOUT_TTL_MINUTES) in str(conn.cursor_obj.executions)

    def test_fresh_incomplete_blocks_second_precheck(self) -> None:
        svc, conn = _service()
        conn.cursor_obj.fetchone_results = [
            None,
            None,
            (50000, "JOD", "monthly_all_access"),
            (1,),  # fresh incomplete inside reserve txn
        ]

        result = svc.run_billing_checkout_precheck("student-sub", DEV_PLAN_ID)

        assert result == {"blockReason": "checkout_in_progress"}
        assert not any("INSERT" in sql.upper() for sql, _ in conn.cursor_obj.executions)

    def test_repo_fresh_incomplete_sql_uses_ttl_param(self) -> None:
        conn = FakeConn()
        repo = SubscriptionRdsRepository(lambda: conn, deployment_environment="dev")
        conn.cursor_obj.fetchone_results = [(1,)]

        assert repo.has_fresh_incomplete_checkout("u", ttl_minutes=30) is True

        sql, params = conn.cursor_obj.executions[0]
        assert "incomplete" in sql
        assert "INTERVAL" in sql
        assert params == ("u", "dev", 30)

    def test_delete_incomplete_checkout_sql(self) -> None:
        conn = FakeConn()
        repo = SubscriptionRdsRepository(lambda: conn, deployment_environment="dev")

        repo.delete_incomplete_checkout("student-sub")

        sql, params = conn.cursor_obj.executions[0]
        assert "DELETE" in sql.upper()
        assert "incomplete" in sql
        assert params == ("student-sub", "dev")
