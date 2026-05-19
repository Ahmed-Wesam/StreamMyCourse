"""W7-P1: get_subscription_summary — manageable rows and 404-path None."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.subscription.repo import SubscriptionRdsRepository


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _repo(*, environment: str = "dev") -> tuple[SubscriptionRdsRepository, FakeConn]:
    conn = FakeConn()
    return SubscriptionRdsRepository(lambda: conn, deployment_environment=environment), conn


def _future_period_end() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)


def _subscription_row(
    status: str,
    *,
    cancel_at_period_end: bool = False,
    period_end: datetime | None = None,
) -> Tuple[Any, ...]:
    end = period_end if period_end is not None else _future_period_end()
    return (status, end, cancel_at_period_end, 50000, "JOD", "monthly")


class TestGetSubscriptionSummary:
    def test_active_future_period_can_cancel_not_reactivate(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [_subscription_row("active")]

        summary = repo.get_subscription_summary("student-sub")

        assert summary is not None
        assert summary.status == "active"
        assert summary.cancel_at_period_end is False
        assert summary.can_cancel is True
        assert summary.can_reactivate is False
        assert summary.past_due is False
        assert summary.amount_minor == 50000
        assert summary.currency == "JOD"
        assert summary.plan_label == "50 JOD / month"
        assert summary.next_billing_date == summary.current_period_end

    def test_canceled_at_period_end_can_reactivate_not_cancel(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [
            _subscription_row("canceled", cancel_at_period_end=True),
        ]

        summary = repo.get_subscription_summary("student-sub")

        assert summary is not None
        assert summary.status == "canceled"
        assert summary.cancel_at_period_end is True
        assert summary.can_cancel is False
        assert summary.can_reactivate is True
        assert summary.next_billing_date is None

    @pytest.mark.parametrize("status", ["expired", "incomplete"])
    def test_non_manageable_status_returns_none(self, status: str) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [_subscription_row(status)]

        assert repo.get_subscription_summary("student-sub") is None

    def test_no_row_returns_none(self) -> None:
        repo, conn = _repo()
        assert repo.get_subscription_summary("student-sub") is None

    def test_past_period_end_returns_none(self) -> None:
        repo, conn = _repo()
        past = datetime.now(timezone.utc) - timedelta(days=1)
        conn.cursor_obj.rows_to_return = [_subscription_row("active", period_end=past)]

        assert repo.get_subscription_summary("student-sub") is None

    def test_empty_user_sub_skips_query(self) -> None:
        repo, conn = _repo()
        assert repo.get_subscription_summary("") is None
        assert not conn.cursor_obj.executions

    def test_sql_joins_plans_and_scopes_environment(self) -> None:
        repo, conn = _repo(environment="prod")
        conn.cursor_obj.rows_to_return = [_subscription_row("active")]

        repo.get_subscription_summary("student-sub")

        sql, params = conn.cursor_obj.executions[0]
        assert "user_subscriptions" in sql
        assert "subscription_plans" in sql
        assert "amount_minor" in sql
        assert params == ("student-sub", "prod")
