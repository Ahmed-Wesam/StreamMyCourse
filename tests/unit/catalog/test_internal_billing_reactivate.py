"""W7-P3b: catalog internal billing.reactivate — RDS restore active without period/provider change."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Sequence, Tuple
from unittest.mock import MagicMock, patch

import pytest

from index import lambda_handler
from services.subscription.internal_manage import (
    handle_internal_billing_reactivate,
    handle_internal_billing_reactivate_prepare,
)
from services.subscription.manage_service import SubscriptionManageService
from services.subscription.repo import ReactivateSubscriptionResult, SubscriptionRdsRepository


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


def _past_period_end() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=1)


class TestReactivateSubscriptionRepo:
    def test_canceled_at_period_end_restores_active_and_clears_cancel_flag(self) -> None:
        repo, conn = _repo()
        period_end = _future_period_end()
        provider_sub_id = "AGR-100"
        conn.cursor_obj.rows_to_return = [
            ("canceled", period_end, True, provider_sub_id),
            (period_end, provider_sub_id),
        ]

        result = repo.reactivate_subscription("student-sub")

        assert result == ReactivateSubscriptionResult(
            outcome="ok",
            current_period_end=period_end,
            provider_subscription_id=provider_sub_id,
        )
        assert len(conn.cursor_obj.executions) == 2
        update_sql, update_params = conn.cursor_obj.executions[1]
        assert "UPDATE user_subscriptions" in update_sql
        assert "status = 'active'" in update_sql
        assert "cancel_at_period_end = FALSE" in update_sql
        assert "canceled_at = NULL" in update_sql
        assert "provider_subscription_id =" not in update_sql
        assert "current_period_end =" not in update_sql
        assert "RETURNING current_period_end, provider_subscription_id" in update_sql
        assert update_params == ("student-sub", "dev")

    def test_preserves_provider_subscription_id_and_current_period_end(self) -> None:
        """UPDATE must not assign provider_subscription_id or current_period_end."""
        repo, conn = _repo()
        period_end = _future_period_end()
        provider_sub_id = "AGR-keep"
        conn.cursor_obj.rows_to_return = [
            ("canceled", period_end, True, provider_sub_id),
            (period_end, provider_sub_id),
        ]

        result = repo.reactivate_subscription("student-sub")

        assert result.outcome == "ok"
        assert result.current_period_end == period_end
        assert result.provider_subscription_id == provider_sub_id
        update_sql, _ = conn.cursor_obj.executions[1]
        assert "provider_subscription_id =" not in update_sql
        assert "current_period_end =" not in update_sql

    def test_active_already_returns_cannot_reactivate(self) -> None:
        """Contract: already-active is not idempotent 200 — maps to cannot_reactivate (409)."""
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [
            ("active", _future_period_end(), False, "AGR-1"),
        ]

        result = repo.reactivate_subscription("student-sub")

        assert result.outcome == "cannot_reactivate"
        assert len(conn.cursor_obj.executions) == 1

    def test_expired_canceled_returns_cannot_reactivate(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [
            ("canceled", _past_period_end(), True, "AGR-1"),
        ]

        result = repo.reactivate_subscription("student-sub")

        assert result.outcome == "cannot_reactivate"
        assert len(conn.cursor_obj.executions) == 1

    def test_incomplete_returns_cannot_reactivate(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [
            ("incomplete", _future_period_end(), False, None),
        ]

        result = repo.reactivate_subscription("student-sub")

        assert result.outcome == "cannot_reactivate"
        assert len(conn.cursor_obj.executions) == 1

    def test_no_row_returns_not_subscribed(self) -> None:
        repo, conn = _repo()
        result = repo.reactivate_subscription("student-sub")
        assert result.outcome == "not_subscribed"
        assert len(conn.cursor_obj.executions) == 1

    def test_empty_user_sub_skips_query(self) -> None:
        repo, conn = _repo()
        result = repo.reactivate_subscription("")
        assert result.outcome == "not_subscribed"
        assert not conn.cursor_obj.executions

    def test_reactivate_prepare_is_read_only(self) -> None:
        repo, conn = _repo()
        period_end = _future_period_end()
        conn.cursor_obj.rows_to_return = [
            ("canceled", period_end, True, "AGR-100"),
        ]

        result = repo.reactivate_prepare("student-sub")

        assert result.outcome == "ok"
        assert result.provider_subscription_id == "AGR-100"
        assert len(conn.cursor_obj.executions) == 1
        select_sql, _ = conn.cursor_obj.executions[0]
        assert "SELECT" in select_sql.upper()
        assert "ORDER BY updated_at DESC" in select_sql
        assert "UPDATE user_subscriptions" not in select_sql


class TestInternalBillingReactivatePrepareHandler:
    def test_prepare_returns_provider_subscription_id(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        manage_svc.reactivate_prepare.return_value = {
            "providerSubscriptionId": "AGR-100",
        }

        out = handle_internal_billing_reactivate_prepare(
            {"internal": "billing.reactivate_prepare", "userSub": "student-sub"},
            manage_service=manage_svc,
        )

        manage_svc.reactivate_prepare.assert_called_once_with(user_sub="student-sub")
        assert out == {"providerSubscriptionId": "AGR-100"}

    def test_prepare_cannot_reactivate_error_code(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        manage_svc.reactivate_prepare.return_value = {"errorCode": "cannot_reactivate"}

        out = handle_internal_billing_reactivate_prepare(
            {"userSub": "student-sub"},
            manage_service=manage_svc,
        )

        assert out == {"errorCode": "cannot_reactivate"}


class TestInternalBillingReactivateHandler:
    def test_success_payload_shape(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        manage_svc.reactivate.return_value = {
            "status": "active",
            "cancelAtPeriodEnd": False,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        }

        out = handle_internal_billing_reactivate(
            {"internal": "billing.reactivate", "userSub": "student-sub"},
            manage_service=manage_svc,
        )

        manage_svc.reactivate.assert_called_once_with(user_sub="student-sub")
        assert out == {
            "status": "active",
            "cancelAtPeriodEnd": False,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        }

    def test_cannot_reactivate_error_code(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        manage_svc.reactivate.return_value = {"errorCode": "cannot_reactivate"}

        out = handle_internal_billing_reactivate(
            {"userSub": "student-sub"},
            manage_service=manage_svc,
        )

        assert out == {"errorCode": "cannot_reactivate"}

    def test_missing_user_sub_raises(self) -> None:
        manage_svc = MagicMock(spec=SubscriptionManageService)
        with pytest.raises(ValueError, match="userSub"):
            handle_internal_billing_reactivate({}, manage_service=manage_svc)


class TestInternalBillingReactivateInvoke:
    def test_lambda_handler_dispatches_reactivate_prepare(self) -> None:
        expected = {"providerSubscriptionId": "AGR-100"}
        with patch("index._handle_internal_billing_event", return_value=expected) as mock:
            event = {
                "internal": "billing.reactivate_prepare",
                "userSub": "cognito-sub-1",
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected

    def test_lambda_handler_dispatches_internal_event(self) -> None:
        expected = {
            "status": "active",
            "cancelAtPeriodEnd": False,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        }
        with patch("index._handle_internal_billing_event", return_value=expected) as mock:
            event = {
                "internal": "billing.reactivate",
                "userSub": "cognito-sub-1",
            }
            out = lambda_handler(event, None)
            mock.assert_called_once_with(event)
            assert out == expected
