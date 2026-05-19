"""PostgreSQL adapter for user_subscriptions granting reads (access-policy-v1)."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

try:  # pragma: no cover - optional dependency path
    import psycopg2
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_GRANTING_SUBSCRIPTION_SQL = """
SELECT 1 FROM user_subscriptions
WHERE user_sub = %s AND environment = %s
  AND current_period_end IS NOT NULL
  AND (
    (status IN ('active', 'past_due')
     AND current_period_end > (NOW() AT TIME ZONE 'UTC'))
    OR
    (status = 'canceled'
     AND cancel_at_period_end = TRUE
     AND current_period_end > (NOW() AT TIME ZONE 'UTC'))
  )
LIMIT 1
"""


class SubscriptionRdsRepository:
    """RDS read model for has_granting_subscription (WS5 catalog access)."""

    def __init__(
        self,
        conn_factory: ConnectionFactory,
        *,
        deployment_environment: str,
    ) -> None:
        self._conn_factory = conn_factory
        self._deployment_environment = (deployment_environment or "dev").strip().lower()
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

    def has_granting_subscription(self, user_sub: str) -> bool:
        """True when a row matches access-policy-v1 granting predicate for this environment."""
        normalized = (user_sub or "").strip()
        if not normalized:
            return False
        cur = self._execute(
            _GRANTING_SUBSCRIPTION_SQL,
            (normalized, self._deployment_environment),
        )
        return cur.fetchone() is not None
