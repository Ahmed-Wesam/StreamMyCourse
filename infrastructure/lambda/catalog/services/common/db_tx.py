"""PostgreSQL transaction helpers (OCC retry, batched delete)."""

from __future__ import annotations

import random
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional, Sequence, TypeVar

T = TypeVar("T")


def _default_sleep(seconds: float) -> None:
    time.sleep(seconds)


def _jittered_backoff(attempt: int, *, base_ms: float = 50.0, cap_ms: float = 1000.0) -> float:
    ceiling = min(cap_ms, base_ms * (2**attempt))
    return random.uniform(0, ceiling) / 1000.0


def run_transaction(
    conn: Any,
    body: Callable[[], T],
    *,
    attempts: int = 3,
    sleep: Optional[Callable[[float], None]] = None,
) -> T:
    """Run ``body`` in a transaction; retry the whole body on ``pgcode == '40001'`` only."""
    sleeper = sleep or _default_sleep
    last_exc: Optional[BaseException] = None
    for attempt in range(attempts):
        conn.autocommit = False
        try:
            result = body()
            conn.commit()
            return result
        except Exception as exc:
            conn.rollback()
            last_exc = exc
            pgcode = getattr(exc, "pgcode", None)
            if pgcode == "40001" and attempt < attempts - 1:
                sleeper(_jittered_backoff(attempt))
                continue
            raise
        finally:
            conn.autocommit = True
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("run_transaction failed without exception")


@contextmanager
def transactional_context(
    conn: Any,
    *,
    attempts: int = 3,
    sleep: Optional[Callable[[float], None]] = None,
) -> Iterator[None]:
    """Context manager with the same OCC retry semantics as :func:`run_transaction`."""
    sleeper = sleep or _default_sleep
    for attempt in range(attempts):
        conn.autocommit = False
        try:
            yield
            conn.commit()
            return
        except Exception as exc:
            conn.rollback()
            pgcode = getattr(exc, "pgcode", None)
            if pgcode == "40001" and attempt < attempts - 1:
                sleeper(_jittered_backoff(attempt))
                continue
            raise
        finally:
            conn.autocommit = True


def delete_in_batches(
    conn: Any,
    delete_sql: str,
    params: Sequence[Any],
    *,
    batch_size: int = 1000,
    sleep: Optional[Callable[[float], None]] = None,
) -> int:
    """Delete in separate transactions until a batch affects zero rows."""
    total = 0
    while True:
        def body() -> int:
            with conn.cursor() as cur:
                cur.execute(delete_sql, params)
                return int(cur.rowcount)

        affected = run_transaction(conn, body, sleep=sleep)
        if affected <= 0:
            break
        total += affected
    return total
