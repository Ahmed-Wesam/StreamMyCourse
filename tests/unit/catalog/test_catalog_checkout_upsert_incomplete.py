"""W6-P1b: upsert incomplete user_subscriptions on checkout precheck."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.subscription.checkout_service import BillingCheckoutService
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


def _service() -> tuple[BillingCheckoutService, SubscriptionRdsRepository, FakeConn]:
    conn = FakeConn()
    repo = SubscriptionRdsRepository(lambda: conn, deployment_environment="dev")
    return BillingCheckoutService(repo), repo, conn


class TestCheckoutUpsertIncomplete:
    def test_precheck_upserts_incomplete_when_not_blocked(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [
            None,  # reactivation check
            None,  # active/past_due block
            (50000, "JOD", "monthly_all_access"),  # plan row
            None,  # fresh incomplete (reserve txn)
        ]
        conn.cursor_obj.rowcount = 0  # update incomplete: no row

        result = svc.run_billing_checkout_precheck("student-sub", DEV_PLAN_ID)

        assert result == {
            "blockReason": None,
            "plan": {
                "amount_minor": 50000,
                "currency": "JOD",
                "plan_key": "monthly_all_access",
            },
        }
        joined = "\n".join(sql for sql, _ in conn.cursor_obj.executions)
        assert "incomplete" in joined.lower()
        assert "INSERT" in joined.upper() or "UPDATE" in joined.upper()

    def test_second_precheck_blocks_via_fresh_incomplete(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [
            None,
            None,
            (50000, "JOD", "monthly_all_access"),
            None,
        ]
        conn.cursor_obj.rowcount = 0
        svc.run_billing_checkout_precheck("student-sub", DEV_PLAN_ID)

        conn.cursor_obj.executions.clear()
        conn.cursor_obj.fetchone_results = [
            None,  # reactivation check
            None,  # active/past_due block
            (50000, "JOD", "monthly_all_access"),
            (1,),  # fresh incomplete row (reserve txn)
        ]

        result = svc.run_billing_checkout_precheck("student-sub", DEV_PLAN_ID)

        assert result == {"blockReason": "checkout_in_progress"}
