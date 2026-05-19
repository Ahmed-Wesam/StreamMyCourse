"""W6-P1e: requires_reactivation_for_checkout SQL (canceled at period end, period not ended)."""

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


class TestReactivationRequiredSql:
    def test_sql_matches_canceled_cancel_at_period_end_future_period(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [(1,)]

        assert repo.requires_reactivation_for_checkout("student-sub") is True

        sql, params = conn.cursor_obj.executions[0]
        assert "user_subscriptions" in sql
        assert "canceled" in sql
        assert "cancel_at_period_end" in sql
        assert "current_period_end" in sql
        assert "NOW() AT TIME ZONE 'UTC'" in sql
        assert params == ("student-sub", "dev")

    def test_returns_false_when_no_matching_row(self) -> None:
        repo, conn = _repo()
        assert repo.requires_reactivation_for_checkout("student-sub") is False

    def test_empty_user_sub_skips_query(self) -> None:
        repo, conn = _repo()
        assert repo.requires_reactivation_for_checkout("") is False
        assert not conn.cursor_obj.executions
