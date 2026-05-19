"""W8-P6 — canceled-in-period checkout precheck returns already_subscribed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

from services.subscription.checkout_service import BillingCheckoutService
from services.subscription.repo import SubscriptionRdsRepository

DEV_PLAN_ID = "a0000000-0000-4000-8000-000000000011"


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    fetchone_results: List[Optional[Tuple[Any, ...]]] = field(default_factory=list)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def test_canceled_in_period_precheck_returns_already_subscribed() -> None:
    conn = FakeConn()
    conn.cursor_obj.fetchone_results = [(1,)]  # in-period granting / blocking row
    repo = SubscriptionRdsRepository(lambda: conn, deployment_environment="dev")
    svc = BillingCheckoutService(repo)

    result = svc.run_billing_checkout_precheck("student-sub", DEV_PLAN_ID)

    assert result == {"blockReason": "already_subscribed"}
    assert len(conn.cursor_obj.executions) == 1
    sql, _params = conn.cursor_obj.executions[0]
    assert "canceled" in sql
    assert "cancel_at_period_end" in sql
