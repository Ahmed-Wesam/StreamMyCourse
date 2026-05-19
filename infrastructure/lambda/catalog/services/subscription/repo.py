"""PostgreSQL adapter for user_subscriptions (access + checkout precheck)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Optional

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

_CHECKOUT_BLOCKING_SUBSCRIPTION_SQL = """
SELECT 1 FROM user_subscriptions
WHERE user_sub = %s AND environment = %s
  AND status IN ('active', 'past_due')
  AND current_period_end IS NOT NULL
  AND current_period_end > (NOW() AT TIME ZONE 'UTC')
LIMIT 1
"""

_HAS_FRESH_INCOMPLETE_CHECKOUT_SQL = """
SELECT 1 FROM user_subscriptions
WHERE user_sub = %s AND environment = %s
  AND status = 'incomplete'
  AND updated_at > (NOW() AT TIME ZONE 'UTC') - (INTERVAL '1 minute' * %s)
LIMIT 1
"""

_DELETE_STALE_INCOMPLETE_CHECKOUT_SQL = """
DELETE FROM user_subscriptions
WHERE user_sub = %s AND environment = %s
  AND status = 'incomplete'
  AND updated_at <= (NOW() AT TIME ZONE 'UTC') - (INTERVAL '1 minute' * %s)
"""

_DELETE_INCOMPLETE_CHECKOUT_SQL = """
DELETE FROM user_subscriptions
WHERE user_sub = %s AND environment = %s
  AND status = 'incomplete'
"""

_REACTIVATION_REQUIRED_CHECKOUT_SQL = """
SELECT 1 FROM user_subscriptions
WHERE user_sub = %s AND environment = %s
  AND status = 'canceled'
  AND cancel_at_period_end = TRUE
  AND current_period_end IS NOT NULL
  AND current_period_end > (NOW() AT TIME ZONE 'UTC')
LIMIT 1
"""

_SUBSCRIPTION_PLAN_FOR_CHECKOUT_SQL = """
SELECT amount_minor, currency, plan_key
FROM subscription_plans
WHERE id = %s::uuid
  AND environment = %s
  AND active = TRUE
LIMIT 1
"""

_UPDATE_INCOMPLETE_SUBSCRIPTION_SQL = """
UPDATE user_subscriptions
SET plan_id = %s::uuid,
    provider = %s,
    status = 'incomplete',
    updated_at = NOW()
WHERE user_sub = %s
  AND environment = %s
  AND status = 'incomplete'
"""

_REOPEN_LAPSED_PAID_FOR_CHECKOUT_SQL = """
UPDATE user_subscriptions
SET plan_id = %s::uuid,
    provider = %s,
    status = 'incomplete',
    updated_at = NOW()
WHERE user_sub = %s
  AND environment = %s
  AND status IN ('active', 'past_due')
  AND (
    current_period_end IS NULL
    OR current_period_end <= (NOW() AT TIME ZONE 'UTC')
  )
"""

_INSERT_INCOMPLETE_SUBSCRIPTION_SQL = """
INSERT INTO user_subscriptions (
    user_sub,
    environment,
    plan_id,
    provider,
    status
)
VALUES (%s, %s, %s::uuid, %s, 'incomplete')
"""


def _is_unique_violation(exc: BaseException) -> bool:
    if psycopg2 is None:
        return False
    if isinstance(exc, psycopg2.IntegrityError) and getattr(exc, "pgcode", None) == "23505":
        return True
    try:
        from psycopg2 import errors as pg_errors

        return isinstance(exc, pg_errors.UniqueViolation)
    except Exception:  # pragma: no cover
        return False


@contextmanager
def _atomic_transaction(conn: Any) -> Iterator[None]:
    conn.autocommit = False
    try:
        yield
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.autocommit = True


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

    def has_checkout_blocking_subscription(self, user_sub: str) -> bool:
        """True when a granting paid row blocks new checkout (active/past_due in period)."""
        normalized = (user_sub or "").strip()
        if not normalized:
            return False
        cur = self._execute(
            _CHECKOUT_BLOCKING_SUBSCRIPTION_SQL,
            (normalized, self._deployment_environment),
        )
        return cur.fetchone() is not None

    def clear_stale_incomplete_checkout(
        self, user_sub: str, *, ttl_minutes: int
    ) -> None:
        """Remove abandoned incomplete rows older than ttl_minutes (UTC updated_at)."""
        normalized = (user_sub or "").strip()
        if not normalized or ttl_minutes <= 0:
            return
        self._execute(
            _DELETE_STALE_INCOMPLETE_CHECKOUT_SQL,
            (normalized, self._deployment_environment, ttl_minutes),
        )

    def has_fresh_incomplete_checkout(
        self, user_sub: str, *, ttl_minutes: int
    ) -> bool:
        """True when a recent incomplete checkout reservation exists (double-click guard)."""
        normalized = (user_sub or "").strip()
        if not normalized or ttl_minutes <= 0:
            return False
        cur = self._execute(
            _HAS_FRESH_INCOMPLETE_CHECKOUT_SQL,
            (normalized, self._deployment_environment, ttl_minutes),
        )
        return cur.fetchone() is not None

    def delete_incomplete_checkout(self, user_sub: str) -> None:
        """Drop incomplete checkout reservation (edge rollback after failed HPP session)."""
        normalized = (user_sub or "").strip()
        if not normalized:
            return
        self._execute(
            _DELETE_INCOMPLETE_CHECKOUT_SQL,
            (normalized, self._deployment_environment),
        )

    def requires_reactivation_for_checkout(self, user_sub: str) -> bool:
        """True when canceled at period end with future current_period_end (WS6 guard only)."""
        normalized = (user_sub or "").strip()
        if not normalized:
            return False
        cur = self._execute(
            _REACTIVATION_REQUIRED_CHECKOUT_SQL,
            (normalized, self._deployment_environment),
        )
        return cur.fetchone() is not None

    def get_subscription_plan_for_checkout(
        self, plan_id: str
    ) -> Optional[dict[str, Any]]:
        normalized_plan = (plan_id or "").strip()
        if not normalized_plan:
            return None
        cur = self._execute(
            _SUBSCRIPTION_PLAN_FOR_CHECKOUT_SQL,
            (normalized_plan, self._deployment_environment),
        )
        row = cur.fetchone()
        if row is None:
            return None
        amount_minor, currency, plan_key = row
        return {
            "amount_minor": int(amount_minor),
            "currency": str(currency),
            "plan_key": str(plan_key),
        }

    def reserve_incomplete_checkout(
        self,
        user_sub: str,
        plan_id: str,
        *,
        ttl_minutes: int,
        provider: str = "paytabs",
    ) -> str:
        """Atomically clear stale incomplete, block fresh/concurrent, or reserve.

        Returns ``reserved`` or ``checkout_in_progress``.
        """
        normalized_sub = (user_sub or "").strip()
        normalized_plan = (plan_id or "").strip()
        if not normalized_sub or not normalized_plan:
            raise ValueError("user_sub and plan_id are required for incomplete reservation")
        if ttl_minutes <= 0:
            raise ValueError("ttl_minutes must be positive")
        conn = self._connection()
        with _atomic_transaction(conn):
            cur = conn.cursor()
            cur.execute(
                _DELETE_STALE_INCOMPLETE_CHECKOUT_SQL,
                (normalized_sub, self._deployment_environment, ttl_minutes),
            )
            cur.execute(
                _HAS_FRESH_INCOMPLETE_CHECKOUT_SQL,
                (normalized_sub, self._deployment_environment, ttl_minutes),
            )
            if cur.fetchone() is not None:
                return "checkout_in_progress"
            update_params = (
                normalized_plan,
                provider,
                normalized_sub,
                self._deployment_environment,
            )
            cur.execute(_UPDATE_INCOMPLETE_SUBSCRIPTION_SQL, update_params)
            if cur.rowcount == 0:
                cur.execute(_REOPEN_LAPSED_PAID_FOR_CHECKOUT_SQL, update_params)
            if cur.rowcount == 0:
                try:
                    cur.execute(
                        _INSERT_INCOMPLETE_SUBSCRIPTION_SQL,
                        (
                            normalized_sub,
                            self._deployment_environment,
                            normalized_plan,
                            provider,
                        ),
                    )
                except Exception as exc:
                    if _is_unique_violation(exc):
                        return "checkout_in_progress"
                    raise
        return "reserved"
