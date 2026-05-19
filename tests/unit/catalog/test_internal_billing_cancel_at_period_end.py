"""W7-P3a: catalog internal billing.cancel_at_period_end — RDS cancel-at-period-end only."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Sequence, Tuple
from unittest.mock import MagicMock, patch

import pytest

from index import lambda_handler
from services.subscription.internal_manage import handle_internal_billing_cancel_at_period_end
from services.subscription.manage_service import SubscriptionManageService
from services.subscription.repo import CancelAtPeriodEndResult, SubscriptionRdsRepository


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    rowcount: int = 0

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


class TestCancelSubscriptionAtPeriodEndRepo:
    def test_active_row_updates_canceled_flags_and_sets_canceled_at(self) -> None:
        repo, conn = _repo()
        period_end = _future_period_end()
        conn.cursor_obj.rows_to_return = [
            ("active", period_end, False),
            (period_end,),
        ]

        result = repo.cancel_subscription_at_period_end("student-sub")

        assert result == CancelAtPeriodEndResult(
            outcome="ok", current_period_end=period_end
        )
        assert len(conn.cursor_obj.executions) == 2
        update_sql, update_params = conn.cursor_obj.executions[1]
        assert "UPDATE user_subscriptions" in update_sql
        assert "status = 'canceled'" in update_sql
        assert "cancel_at_period_end = TRUE" in update_sql
        assert "canceled_at = NOW() AT TIME ZONE 'UTC'" in update_sql
        assert "RETURNING current_period_end" in update_sql
        assert update_params == ("student-sub", "dev")

    def test_already_canceled_in_period_returns_already_canceled_without_update(self) -> None:
        """Contract: edge maps to 409 already_canceled (not idempotent 200)."""
        repo, conn = _repo()
        period_end = _future_period_end()
        conn.cursor_obj.rows_to_return = [
            ("canceled", period_end, True),
        ]

        result = repo.cancel_subscription_at_period_end("student-sub")

        assert result.outcome == "already_canceled"
        assert len(conn.cursor_obj.executions) == 1

    def test_incomplete_returns_cannot_cancel(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [
            ("incomplete", _future_period_end(), False),
        ]

        result = repo.cancel_subscription_at_period_end("student-sub")

        assert result.outcome == "cannot_cancel"
        assert len(conn.cursor_obj.executions) == 1

    def test_no_row_returns_not_subscribed(self) -> None:
        repo, conn = _repo()
        result = repo.cancel_subscription_at_period_end("student-sub")
        assert result.outcome == "not_subscribed"
        assert len(conn.cursor_obj.executions) == 1

    def test_empty_user_sub_skips_query(self) -> None:
        repo, conn = _repo()
        result = repo.cancel_subscription_at_period_end("")
        assert result.outcome == "not_subscribed"
        assert not conn.cursor_obj.executions


class TestInternalBillingCancelAtPeriodEndHandler:
    def test_success_payload_shape(self) -> None:
        period_end = _future_period_end()
        manage_svc = MagicMock(spec=SubscriptionManageService)
        manage_svc.cancel_at_period_end.return_value = {
            "status": "canceled",
            "cancelAtPeriodEnd": True,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        }

        out = handle_internal_billing_cancel_at_period_end(
            {"internal": "billing.cancel_at_period_end", "userSub": "student-sub"},
            manage_service=manage_svc,
        )

        manage_svc.cancel_at_period_end.assert_called_once_with(user_sub="student-sub")
        assert out == {
            "status": "canceled",
            "cancelAtPeriodEnd": True,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        }

    def test_already_canceled_error_code(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        manage_svc.cancel_at_period_end.return_value = {"errorCode": "already_canceled"}

        out = handle_internal_billing_cancel_at_period_end(
            {"userSub": "student-sub"},
            manage_service=manage_svc,
        )

        assert out == {"errorCode": "already_canceled"}

    def test_incomplete_maps_to_cannot_cancel(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        manage_svc.cancel_at_period_end.return_value = {"errorCode": "cannot_cancel"}

        out = handle_internal_billing_cancel_at_period_end(
            {"userSub": "student-sub"},
            manage_service=manage_svc,
        )

        assert out == {"errorCode": "cannot_cancel"}

    def test_missing_user_sub_raises(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        with pytest.raises(ValueError, match="userSub"):
            handle_internal_billing_cancel_at_period_end({}, manage_service=manage_svc)


class TestInternalBillingCancelAtPeriodEndInvoke:
    def test_lambda_handler_dispatches_internal_event(self) -> None:
        expected = {
            "status": "canceled",
            "cancelAtPeriodEnd": True,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        }
        with patch("index._handle_internal_billing_event", return_value=expected) as mock:
            event = {
                "internal": "billing.cancel_at_period_end",
                "userSub": "cognito-sub-1",
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected
