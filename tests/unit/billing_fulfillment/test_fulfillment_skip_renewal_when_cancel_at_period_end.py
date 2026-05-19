"""W7-P3c: fulfillment must not clobber cancel-at-period-end via renewal IPNs."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

import pytest

_FULFILL_SRC = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "lambda" / "billing_fulfillment"
)
if str(_FULFILL_SRC) not in sys.path:
    sys.path.append(str(_FULFILL_SRC))

from domain_events import BillingDomainEvent  # noqa: E402
from fulfillment_repo import process_event_in_transaction  # noqa: E402


def _event(**overrides: object) -> BillingDomainEvent:
    base: dict[str, Any] = dict(
        event_type="subscription.renewed",
        provider="paytabs",
        provider_event_id="paytabs:TST1:renew-1",
        environment="dev",
        user_sub="cognito-sub-1",
        plan_id="a0000000-0000-4000-8000-000000000011",
        payload_digest="a" * 64,
        provider_subscription_id="AGR-1",
        current_period_start="2026-05-01T00:00:00Z",
        current_period_end="2026-06-01T00:00:00Z",
    )
    base.update(overrides)
    return BillingDomainEvent(**base)  # type: ignore[arg-type]


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Optional[Tuple[Any, ...]]] = field(default_factory=list)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def close(self) -> None:
        pass


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _subscription_update_sqls(executions: List[Tuple[str, Tuple[Any, ...]]]) -> List[str]:
    return [sql for sql, _ in executions if "UPDATE user_subscriptions" in sql]


class TestFulfillmentSkipWhenCancelAtPeriodEnd:
    def test_renewed_ipn_skipped_when_row_canceled_at_period_end(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [
            ("webhook-id-1",),
            ("canceled", True),
        ]
        evt = _event(event_type="subscription.renewed")

        result = process_event_in_transaction(conn, evt)

        assert result.recorded is True
        assert result.subscription_updated is False
        assert _subscription_update_sqls(conn.cursor_obj.executions) == []

    @pytest.mark.parametrize(
        "event_type",
        [
            "subscription.activated",
            "subscription.renewed",
            "subscription.payment_failed",
        ],
    )
    def test_granting_ipns_skipped_when_cancel_at_period_end(
        self, event_type: str
    ) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [
            ("webhook-id-1",),
            ("canceled", True),
        ]
        evt = _event(event_type=event_type)

        result = process_event_in_transaction(conn, evt)

        assert result.subscription_updated is False
        assert _subscription_update_sqls(conn.cursor_obj.executions) == []

    def test_canceled_ipn_still_updates_when_event_confirms_period_end(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [
            ("webhook-id-1",),
            ("canceled", True),
            None,
            ("sub-row-id",),
        ]
        evt = _event(
            event_type="subscription.canceled",
            provider_event_id="paytabs:TST1:cancel-1",
            cancel_at_period_end=True,
            canceled_at="2026-05-18T12:00:00Z",
        )

        result = process_event_in_transaction(conn, evt)

        assert result.recorded is True
        assert result.subscription_updated is True
        assert len(_subscription_update_sqls(conn.cursor_obj.executions)) == 1

    def test_paytabs_immediate_cancel_ipn_skipped_when_student_cancel_at_period_end(
        self,
    ) -> None:
        """PayTabs Agreement cancel maps cancel_at_period_end=False; must not revoke access early."""
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [
            ("webhook-id-1",),
            ("canceled", True),
        ]
        evt = _event(
            event_type="subscription.canceled",
            provider_event_id="paytabs:TST1:cancel-immediate",
            cancel_at_period_end=False,
            canceled_at="2026-05-18T12:00:00Z",
        )

        result = process_event_in_transaction(conn, evt)

        assert result.recorded is True
        assert result.subscription_updated is False
        assert _subscription_update_sqls(conn.cursor_obj.executions) == []
