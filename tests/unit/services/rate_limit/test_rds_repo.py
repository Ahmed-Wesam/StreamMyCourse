"""Unit tests for ``RateLimitRdsRepository.consume`` (mocked psycopg2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.rate_limit.rds_repo import RateLimitRdsRepository


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    rowcount: int = 1
    closed: bool = False

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def close(self) -> None:
        self.closed = True


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


@pytest.fixture
def fake_conn() -> FakeConn:
    return FakeConn()


@pytest.fixture
def repo(fake_conn: FakeConn) -> RateLimitRdsRepository:
    return RateLimitRdsRepository(lambda: fake_conn)


def _window_start(*, window_seconds: int, now: datetime | None = None) -> datetime:
    now = now or datetime(2026, 5, 28, 12, 0, 30, tzinfo=timezone.utc)
    epoch = int(now.timestamp())
    window_epoch = (epoch // window_seconds) * window_seconds
    return datetime.fromtimestamp(window_epoch, tz=timezone.utc)


class TestRateLimitRdsRepositoryConsume:
    def test_new_window_starts_count_one_and_allowed(
        self, repo: RateLimitRdsRepository, fake_conn: FakeConn, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = datetime(2026, 5, 28, 12, 0, 30, tzinfo=timezone.utc)
        monkeypatch.setattr(
            "services.rate_limit.rds_repo._utc_now",
            lambda: now,
        )
        ws = _window_start(window_seconds=60, now=now)
        fake_conn.cursor_obj.rows_to_return = [(1, ws)]

        result = repo.consume("rl:test:actor:1", window_seconds=60, max_count=6)

        assert result.allowed is True
        assert result.retry_after_seconds == 0
        assert fake_conn.committed == 1
        sql, params = fake_conn.cursor_obj.executions[0]
        assert "rate_limit_counters" in sql
        assert params[0] == "rl:test:actor:1"
        assert params[1] == ws

    def test_same_window_increments_and_allowed_under_max(
        self, repo: RateLimitRdsRepository, fake_conn: FakeConn, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = datetime(2026, 5, 28, 12, 0, 45, tzinfo=timezone.utc)
        monkeypatch.setattr("services.rate_limit.rds_repo._utc_now", lambda: now)
        ws = _window_start(window_seconds=60, now=now)
        fake_conn.cursor_obj.rows_to_return = [(3, ws)]

        result = repo.consume("rl:test:actor:1", window_seconds=60, max_count=6)

        assert result.allowed is True
        assert result.retry_after_seconds == 0

    def test_at_max_returns_denied_with_retry_after(
        self, repo: RateLimitRdsRepository, fake_conn: FakeConn, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = datetime(2026, 5, 28, 12, 0, 50, tzinfo=timezone.utc)
        monkeypatch.setattr("services.rate_limit.rds_repo._utc_now", lambda: now)
        ws = _window_start(window_seconds=60, now=now)
        fake_conn.cursor_obj.rows_to_return = [(7, ws)]

        result = repo.consume("rl:test:actor:1", window_seconds=60, max_count=6)

        assert result.allowed is False
        window_end = ws + timedelta(seconds=60)
        assert result.retry_after_seconds == int((window_end - now).total_seconds())

    def test_expired_window_resets_to_count_one(
        self, repo: RateLimitRdsRepository, fake_conn: FakeConn, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = datetime(2026, 5, 28, 12, 2, 0, tzinfo=timezone.utc)
        monkeypatch.setattr("services.rate_limit.rds_repo._utc_now", lambda: now)
        new_ws = _window_start(window_seconds=60, now=now)
        fake_conn.cursor_obj.rows_to_return = [(1, new_ws)]

        result = repo.consume("rl:test:actor:1", window_seconds=60, max_count=6)

        assert result.allowed is True
        assert result.retry_after_seconds == 0
        _, params = fake_conn.cursor_obj.executions[0]
        assert params[1] == new_ws

    def test_fetchone_none_raises(
        self, repo: RateLimitRdsRepository, fake_conn: FakeConn, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "services.rate_limit.rds_repo._utc_now",
            lambda: datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(RuntimeError, match="rate limit consume"):
            repo.consume("rl:test", window_seconds=60, max_count=1)

    def test_execute_failure_before_connection_does_not_raise_name_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _fail_factory() -> FakeConn:
            raise OSError("connection refused")

        repo = RateLimitRdsRepository(_fail_factory)
        monkeypatch.setattr(
            "services.rate_limit.rds_repo._utc_now",
            lambda: datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc),
        )
        with pytest.raises(OSError, match="connection refused"):
            repo.consume("rl:test", window_seconds=60, max_count=1)
