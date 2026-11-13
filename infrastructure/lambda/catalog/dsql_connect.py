"""Aurora DSQL connection helper (IAM token via aurora-dsql-python-connector)."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

DSQL_CONNECTION_RECYCLE_SECONDS = 3300
DSQL_DBNAME = "postgres"
DSQL_SSLMODE = "require"
DSQL_RUNTIME_USER = "smc_app"
DSQL_SCHEMA = "app"

ConnectionFactory = Callable[[], Any]

logger = logging.getLogger(__name__)


def connection_error(host: str, exc: BaseException) -> RuntimeError:
    """Rewrite connection failures so logs/exceptions contain only the host."""
    err = RuntimeError(f"DSQL connection failed for host {host}")
    err.__cause__ = exc
    return err


def _configure_new_connection(conn: Any) -> None:
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {DSQL_SCHEMA}")


def connect(user: str, host: str) -> Any:
    """Open a psycopg2 connection to Aurora DSQL (admin or smc_app)."""
    host = (host or "").strip()
    if not host:
        raise ValueError("DSQL host is required")
    try:
        import aurora_dsql_psycopg2  # type: ignore[import-untyped]
    except ImportError as exc:
        raise connection_error(host, exc) from None
    try:
        conn = aurora_dsql_psycopg2.connect(
            user=user,
            host=host,
            dbname=DSQL_DBNAME,
            sslmode=DSQL_SSLMODE,
        )
    except Exception as exc:
        raise connection_error(host, exc) from None
    _configure_new_connection(conn)
    return conn


class _RecyclingConnection:
    """Proxy that refreshes the underlying connection after recycle interval."""

    def __init__(self, host: str, user: str) -> None:
        self._host = host
        self._user = user
        self._conn: Any | None = None
        self._opened_at = 0.0

    def _refresh_if_stale(self) -> None:
        now = time.monotonic()
        if self._conn is not None and now - self._opened_at >= DSQL_CONNECTION_RECYCLE_SECONDS:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
        if self._conn is None:
            self._conn = connect(self._user, self._host)
            self._opened_at = now

    def __getattr__(self, name: str) -> Any:
        self._refresh_if_stale()
        assert self._conn is not None
        return getattr(self._conn, name)

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            finally:
                self._conn = None


def build_connection_factory(host: str, *, user: str = DSQL_RUNTIME_USER) -> ConnectionFactory:
    """Lambda/runtime factory: ``smc_app``, ``search_path=app``, recycle at 3300s."""
    host = (host or "").strip()
    if not host:
        raise ValueError("DSQL host is required")
    holder = _RecyclingConnection(host, user)

    def factory() -> Any:
        holder._refresh_if_stale()
        assert holder._conn is not None
        return holder._conn

    return factory
