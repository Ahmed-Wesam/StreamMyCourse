"""PostgreSQL adapter for fixed-window rate limit counters."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from services.rate_limit.models import RateLimitResult

try:  # pragma: no cover - optional dependency path
    import psycopg2
    from psycopg2 import OperationalError
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]
    OperationalError = Exception  # type: ignore[misc, assignment]


logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_CONSUME_SQL = """
INSERT INTO rate_limit_counters (bucket_key, window_start, count)
VALUES (%s, %s, 1)
ON CONFLICT (bucket_key) DO UPDATE SET
    window_start = CASE
        WHEN rate_limit_counters.window_start + make_interval(secs => %s) <= NOW()
        THEN EXCLUDED.window_start
        ELSE rate_limit_counters.window_start
    END,
    count = CASE
        WHEN rate_limit_counters.window_start + make_interval(secs => %s) <= NOW()
        THEN 1
        ELSE rate_limit_counters.count + 1
    END
RETURNING count, window_start
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _window_start_for_now(*, window_seconds: int, now: datetime) -> datetime:
    epoch = int(now.timestamp())
    window_epoch = (epoch // window_seconds) * window_seconds
    return datetime.fromtimestamp(window_epoch, tz=timezone.utc)


class RateLimitRdsRepository:
    """PostgreSQL repository for ``rate_limit_counters`` (lazy window expiry on read)."""

    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _execute(
        self, sql: str, params: tuple = (), *, commit: bool = False
    ) -> Any:
        conn: Optional[Any] = None
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            return cur
        except Exception as exc:
            if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
                logger.warning(
                    "RDS connection lost, reconnecting and retrying once: %s", exc
                )
                self._conn = None
                try:
                    conn = self._connection()
                    cur = conn.cursor()
                    cur.execute(sql, params)
                    if commit:
                        conn.commit()
                    return cur
                except Exception:
                    if conn is not None:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    raise
            if conn is not None:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise

    def consume(
        self,
        bucket_key: str,
        window_seconds: int,
        max_count: int,
    ) -> RateLimitResult:
        """Record one request; reset the window when the stored window has expired."""
        now = _utc_now()
        current_window_start = _window_start_for_now(
            window_seconds=window_seconds,
            now=now,
        )
        cur = self._execute(
            _CONSUME_SQL,
            (
                bucket_key,
                current_window_start,
                window_seconds,
                window_seconds,
            ),
            commit=True,
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("rate limit consume returned no row")

        count = int(row[0])
        window_start = row[1]
        if not isinstance(window_start, datetime):
            raise RuntimeError("rate limit consume returned invalid window_start")

        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=timezone.utc)

        allowed = count <= max_count
        if allowed:
            return RateLimitResult(allowed=True, retry_after_seconds=0)

        window_end = window_start + timedelta(seconds=window_seconds)
        retry_after = max(1, int((window_end - now).total_seconds()))
        return RateLimitResult(allowed=False, retry_after_seconds=retry_after)
