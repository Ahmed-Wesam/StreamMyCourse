"""W6-P1a: has_checkout_blocking_subscription SQL (active / past_due only)."""

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

    @property
    def rowcount(self) -> int:
        return 1 if self.rows_to_return else 0


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


class TestCheckoutBlockingSubscriptionSql:
    def test_sql_targets_blocking_statuses_only(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rows_to_return = [(1,)]

        assert repo.has_checkout_blocking_subscription("student-sub") is True

        sql, params = conn.cursor_obj.executions[0]
        assert "user_subscriptions" in sql
        assert "active" in sql
        assert "past_due" in sql
        assert "current_period_end" in sql
        assert "incomplete" not in sql
        assert "expired" not in sql.lower() or "status in" in sql.lower()
        assert params == ("student-sub", "dev")

    @pytest.mark.parametrize(
        "has_row,expected",
        [(True, True), (False, False)],
    )
    def test_returns_bool_from_fetchone(self, has_row: bool, expected: bool) -> None:
        repo, conn = _repo()
        if has_row:
            conn.cursor_obj.rows_to_return = [(1,)]
        assert repo.has_checkout_blocking_subscription("u") is expected

    def test_empty_user_sub_skips_query(self) -> None:
        repo, conn = _repo()
        assert repo.has_checkout_blocking_subscription("") is False
        assert repo.has_checkout_blocking_subscription("   ") is False
        assert not conn.cursor_obj.executions
