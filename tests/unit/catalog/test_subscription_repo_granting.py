"""W5-P1: has_granting_subscription SQL and environment scoping."""

from __future__ import annotations

from dataclasses import dataclass, field
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


class TestSubscriptionGrantingSql:
    def test_sql_targets_user_subscriptions_with_null_safe_period_end(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [(1,)]

        repo.has_granting_subscription("student-sub")

        sql, params = conn.cursor_obj.executions[0]
        assert "user_subscriptions" in sql
        assert "current_period_end IS NOT NULL" in sql
        assert "'active'" in sql or "active" in sql
        assert "past_due" in sql
        assert "cancel_at_period_end" in sql
        assert "NOW() AT TIME ZONE 'UTC'" in sql
        assert params == ("student-sub", "dev")

    @pytest.mark.parametrize(
        "environment,expected_env_param",
        [
            ("dev", "dev"),
            ("prod", "prod"),
            ("  PROD  ", "prod"),
        ],
    )
    def test_environment_scoping(self, environment: str, expected_env_param: str) -> None:
        repo, conn = _repo(environment=environment)
        conn.cursor_obj.rows_to_return = [(1,)]

        repo.has_granting_subscription("user-1")

        _, params = conn.cursor_obj.executions[0]
        assert params[1] == expected_env_param


@pytest.mark.parametrize(
    "scenario",
    [
        "active_future_period",
        "past_due_future_period",
        "canceled_cancel_at_period_end_future",
    ],
)
def test_granting_scenarios_return_true_when_row_exists(scenario: str) -> None:
    """DB rows matching access-policy-v1 grant; adapter returns True on SELECT 1 hit."""
    repo, conn = _repo()
    conn.cursor_obj.rows_to_return = [(1,)]

    assert repo.has_granting_subscription("student-sub") is True
    assert conn.cursor_obj.executions, f"{scenario}: expected one query"


@pytest.mark.parametrize(
    "scenario",
    [
        "canceled_immediate",
        "expired",
        "incomplete",
        "null_current_period_end",
    ],
)
def test_non_granting_scenarios_return_false_when_no_row(scenario: str) -> None:
    """Statuses/NULL period excluded by SQL; adapter returns False when fetchone is empty."""
    repo, conn = _repo()

    assert repo.has_granting_subscription("student-sub") is False


def test_returns_false_for_empty_user_sub_without_query() -> None:
    repo, conn = _repo()

    assert repo.has_granting_subscription("") is False
    assert repo.has_granting_subscription("   ") is False
    assert not conn.cursor_obj.executions
