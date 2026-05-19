"""PostgreSQL adapter for user_subscriptions (access + checkout precheck)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Optional

try:  # pragma: no cover - optional dependency path
    import psycopg2
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_FILS_PER_JOD = 1000


@dataclass(frozen=True)
class CancelAtPeriodEndResult:
    """Outcome of cancel-at-period-end RDS update (internal manage invoke)."""

    outcome: str  # ok | already_canceled | not_subscribed | cannot_cancel
    current_period_end: Optional[datetime] = None
    provider_subscription_id: Optional[str] = None


@dataclass(frozen=True)
class SubscriptionSummary:
    """Manageable subscription read model (WS7 GET /billing/subscription)."""

    status: str
    current_period_end: datetime
    cancel_at_period_end: bool
    can_cancel: bool
    next_billing_date: Optional[datetime]
    amount_minor: int
    currency: str
    plan_label: str
    past_due: bool

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

_CHECKOUT_BLOCKING_SUBSCRIPTION_SQL = _GRANTING_SUBSCRIPTION_SQL

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

_GET_SUBSCRIPTION_SUMMARY_SQL = """
SELECT
  us.status,
  us.current_period_end,
  us.cancel_at_period_end,
  sp.amount_minor,
  sp.currency,
  sp.billing_interval
FROM user_subscriptions us
INNER JOIN subscription_plans sp
  ON us.plan_id = sp.id AND us.environment = sp.environment
WHERE us.user_sub = %s
  AND us.environment = %s
ORDER BY us.updated_at DESC
LIMIT 1
"""

_SELECT_SUBSCRIPTION_CANCEL_STATE_SQL = """
SELECT status, current_period_end, cancel_at_period_end, provider_subscription_id
FROM user_subscriptions
WHERE user_sub = %s
  AND environment = %s
ORDER BY updated_at DESC
LIMIT 1
"""

_CANCEL_SUBSCRIPTION_AT_PERIOD_END_SQL = """
UPDATE user_subscriptions
SET status = 'canceled',
    cancel_at_period_end = TRUE,
    canceled_at = NOW() AT TIME ZONE 'UTC',
    updated_at = NOW()
WHERE user_sub = %s
  AND environment = %s
  AND status IN ('active', 'past_due')
  AND cancel_at_period_end = FALSE
  AND current_period_end IS NOT NULL
  AND current_period_end > (NOW() AT TIME ZONE 'UTC')
RETURNING current_period_end, provider_subscription_id
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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_plan_label(amount_minor: int, currency: str, billing_interval: str) -> str:
    major = amount_minor // _FILS_PER_JOD
    interval_label = "month" if (billing_interval or "").strip().lower() == "monthly" else billing_interval
    return f"{major} {currency} / {interval_label}"


def _is_manageable_subscription(
    status: str,
    *,
    period_end: Optional[datetime],
    cancel_at_period_end: bool,
    now_utc: datetime,
) -> bool:
    if period_end is None:
        return False
    end_utc = _as_utc_aware(period_end)
    if end_utc <= now_utc:
        return False
    normalized = (status or "").strip().lower()
    if normalized in ("active", "past_due"):
        return True
    if normalized == "canceled" and cancel_at_period_end:
        return True
    return False


def _build_subscription_summary(
    status: str,
    period_end: datetime,
    cancel_at_period_end: bool,
    amount_minor: int,
    currency: str,
    billing_interval: str,
    *,
    now_utc: datetime,
) -> SubscriptionSummary:
    end_utc = _as_utc_aware(period_end)
    normalized = (status or "").strip().lower()
    period_in_future = end_utc > now_utc
    can_cancel = (
        normalized in ("active", "past_due")
        and not cancel_at_period_end
        and period_in_future
    )
    next_billing: Optional[datetime]
    if normalized in ("active", "past_due"):
        next_billing = end_utc
    else:
        next_billing = None
    return SubscriptionSummary(
        status=normalized,
        current_period_end=end_utc,
        cancel_at_period_end=bool(cancel_at_period_end),
        can_cancel=can_cancel,
        next_billing_date=next_billing,
        amount_minor=int(amount_minor),
        currency=str(currency),
        plan_label=_format_plan_label(int(amount_minor), str(currency), str(billing_interval)),
        past_due=normalized == "past_due",
    )


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
        """True when in-period granting access blocks new checkout (same predicate as access)."""
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

    def cancel_subscription_at_period_end(self, user_sub: str) -> CancelAtPeriodEndResult:
        """Cancel at period end for active/past_due in-period rows (internal manage only)."""
        normalized = (user_sub or "").strip()
        if not normalized:
            return CancelAtPeriodEndResult(outcome="not_subscribed")

        cur = self._execute(
            _SELECT_SUBSCRIPTION_CANCEL_STATE_SQL,
            (normalized, self._deployment_environment),
        )
        row = cur.fetchone()
        if row is None:
            return CancelAtPeriodEndResult(outcome="not_subscribed")

        status, period_end, cancel_at_period_end, provider_id = row
        now_utc = _utc_now()
        normalized_status = (str(status) or "").strip().lower()
        provider_subscription_id = (
            str(provider_id).strip() if provider_id is not None else None
        ) or None

        if normalized_status == "incomplete":
            return CancelAtPeriodEndResult(outcome="cannot_cancel")

        if (
            normalized_status == "canceled"
            and bool(cancel_at_period_end)
            and period_end is not None
            and _as_utc_aware(period_end) > now_utc
        ):
            return CancelAtPeriodEndResult(
                outcome="already_canceled",
                current_period_end=_as_utc_aware(period_end),
                provider_subscription_id=provider_subscription_id,
            )

        if normalized_status in ("active", "past_due") and not bool(cancel_at_period_end):
            if period_end is None or _as_utc_aware(period_end) <= now_utc:
                return CancelAtPeriodEndResult(outcome="cannot_cancel")
            cur = self._execute(
                _CANCEL_SUBSCRIPTION_AT_PERIOD_END_SQL,
                (normalized, self._deployment_environment),
            )
            updated = cur.fetchone()
            if updated is None:
                return CancelAtPeriodEndResult(outcome="cannot_cancel")
            period_end_utc = _as_utc_aware(updated[0])
            provider_id = updated[1] if len(updated) > 1 else None
            provider_subscription_id = (
                str(provider_id).strip() if provider_id is not None else None
            ) or None
            return CancelAtPeriodEndResult(
                outcome="ok",
                current_period_end=period_end_utc,
                provider_subscription_id=provider_subscription_id,
            )

        if not _is_manageable_subscription(
            normalized_status,
            period_end=period_end,
            cancel_at_period_end=bool(cancel_at_period_end),
            now_utc=now_utc,
        ):
            return CancelAtPeriodEndResult(outcome="not_subscribed")

        return CancelAtPeriodEndResult(outcome="cannot_cancel")

    def get_subscription_summary(self, user_sub: str) -> Optional[SubscriptionSummary]:
        """Return manageable subscription summary or None (GET 404 not_subscribed path)."""
        normalized = (user_sub or "").strip()
        if not normalized:
            return None
        cur = self._execute(
            _GET_SUBSCRIPTION_SUMMARY_SQL,
            (normalized, self._deployment_environment),
        )
        row = cur.fetchone()
        if row is None:
            return None
        (
            status,
            period_end,
            cancel_at_period_end,
            amount_minor,
            currency,
            billing_interval,
        ) = row
        now_utc = _utc_now()
        if not _is_manageable_subscription(
            str(status),
            period_end=period_end,
            cancel_at_period_end=bool(cancel_at_period_end),
            now_utc=now_utc,
        ):
            return None
        if period_end is None:
            return None
        return _build_subscription_summary(
            str(status),
            period_end,
            bool(cancel_at_period_end),
            int(amount_minor),
            str(currency),
            str(billing_interval),
            now_utc=now_utc,
        )

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
