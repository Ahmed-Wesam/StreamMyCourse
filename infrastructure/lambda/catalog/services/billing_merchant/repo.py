"""PostgreSQL adapter for ``teacher_merchant_accounts`` (merchant status reads)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

try:  # pragma: no cover - optional dependency path
    import psycopg2
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_MERCHANT_COLUMNS = (
    "environment, teacher_sub, provider, provider_profile_id, "
    "payout_ready, payout_ready_at, created_at, updated_at"
)


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def _row_to_merchant(row: Tuple[Any, ...]) -> Dict[str, Any]:
    (
        _environment,
        _teacher_sub,
        provider,
        provider_profile_id,
        payout_ready,
        payout_ready_at,
        _created_at,
        _updated_at,
    ) = row
    profile_id = str(provider_profile_id).strip() if provider_profile_id is not None else ""
    return {
        "provider": str(provider or "paytabs"),
        "providerProfileId": profile_id or None,
        "payoutReady": bool(payout_ready),
        "payoutReadyAt": _to_iso(payout_ready_at) or None,
    }


class MerchantAccountRdsRepository:
    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _execute(self, sql: str, params: tuple = ()) -> Any:
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            return cur
        except Exception as exc:
            if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
                logger.warning("RDS connection lost, reconnecting and retrying once: %s", exc)
                self._conn = None
                conn = self._connection()
                cur = conn.cursor()
                cur.execute(sql, params)
                return cur
            conn.rollback()
            raise

    def get_merchant_account(self, *, environment: str) -> Optional[Dict[str, Any]]:
        cur = self._execute(
            f"""
            SELECT {_MERCHANT_COLUMNS}
            FROM teacher_merchant_accounts
            WHERE environment = %s
            """,
            (environment,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return _row_to_merchant(row)
