"""PostgreSQL adapter for bundle_offers, purchases, and course prices (RS-5)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Optional

try:  # pragma: no cover
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

from services.purchases.models import BundleOffer, PurchaseRecord

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_HAS_PAID_COURSE_PURCHASE_SQL = """
SELECT 1 FROM purchases
WHERE user_sub = %s AND environment = %s
  AND product_type = 'course'
  AND course_id = %s::uuid
  AND status = 'paid'
LIMIT 1
"""

_HAS_PAID_BUNDLE_SQL = """
SELECT 1 FROM purchases
WHERE user_sub = %s AND environment = %s
  AND product_type = 'bundle'
  AND status = 'paid'
LIMIT 1
"""

_GET_BUNDLE_OFFER_SQL = """
SELECT amount_minor, currency
FROM bundle_offers
WHERE environment = %s AND active = TRUE
LIMIT 1
"""

_SET_BUNDLE_PRICE_SQL = """
UPDATE bundle_offers
SET amount_minor = %s, updated_at = NOW()
WHERE environment = %s
"""

_SET_COURSE_PRICE_SQL = """
UPDATE courses
SET price_amount_minor = %s, updated_at = NOW()
WHERE id = %s::uuid
"""

_GET_COURSE_PRICE_SQL = """
SELECT price_amount_minor
FROM courses
WHERE id = %s::uuid
LIMIT 1
"""

_LIST_PURCHASES_FOR_USER_SQL = """
SELECT id, product_type, course_id, status, amount_minor, currency, created_at
FROM purchases
WHERE user_sub = %s AND environment = %s AND status = 'paid'
ORDER BY created_at DESC
"""

_HAS_FRESH_PENDING_CHECKOUT_SQL = """
SELECT 1 FROM purchases
WHERE user_sub = %s AND environment = %s
  AND status = 'pending'
  AND product_type = %s
  AND (
    (product_type = 'course' AND course_id = %s::uuid)
    OR (product_type = 'bundle' AND course_id IS NULL)
  )
  AND updated_at > (NOW() AT TIME ZONE 'UTC') - (INTERVAL '1 minute' * %s)
LIMIT 1
"""

_DELETE_STALE_PENDING_CHECKOUT_SQL = """
DELETE FROM purchases
WHERE user_sub = %s AND environment = %s
  AND status = 'pending'
  AND product_type = %s
  AND (
    (product_type = 'course' AND course_id = %s::uuid)
    OR (product_type = 'bundle' AND course_id IS NULL)
  )
  AND updated_at <= (NOW() AT TIME ZONE 'UTC') - (INTERVAL '1 minute' * %s)
"""

_DELETE_PENDING_CHECKOUT_SQL = """
DELETE FROM purchases
WHERE user_sub = %s AND environment = %s
  AND status = 'pending'
  AND product_type = %s
  AND (
    (product_type = 'course' AND course_id = %s::uuid)
    OR (product_type = 'bundle' AND course_id IS NULL)
  )
"""

_INSERT_PENDING_COURSE_PURCHASE_SQL = """
INSERT INTO purchases (
    user_sub,
    environment,
    product_type,
    course_id,
    status,
    amount_minor,
    currency,
    provider
)
VALUES (%s, %s, 'course', %s::uuid, 'pending', %s, %s, %s)
RETURNING id::text
"""

_INSERT_PENDING_BUNDLE_PURCHASE_SQL = """
INSERT INTO purchases (
    user_sub,
    environment,
    product_type,
    course_id,
    status,
    amount_minor,
    currency,
    provider
)
VALUES (%s, %s, 'bundle', NULL, 'pending', %s, %s, %s)
RETURNING id::text
"""


def _as_utc_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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


class PurchaseRdsRepository:
    """RDS adapter for purchase entitlements, pricing, and checkout precheck."""

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
            conn = self._connection()
            conn.rollback()
            raise

    def _product_params(self, product_type: str, course_id: str | None) -> tuple[str, str | None]:
        normalized_type = (product_type or "").strip().lower()
        if normalized_type not in ("course", "bundle"):
            raise ValueError(f"invalid product_type: {product_type!r}")
        if normalized_type == "course":
            normalized_course = (course_id or "").strip()
            if not normalized_course:
                raise ValueError("course_id is required for course checkout")
            return normalized_type, normalized_course
        return normalized_type, None

    def has_paid_course_purchase(self, user_sub: str, course_id: str) -> bool:
        normalized_sub = (user_sub or "").strip()
        normalized_course = (course_id or "").strip()
        if not normalized_sub or not normalized_course:
            return False
        cur = self._execute(
            _HAS_PAID_COURSE_PURCHASE_SQL,
            (normalized_sub, self._deployment_environment, normalized_course),
        )
        return cur.fetchone() is not None

    def has_paid_bundle(self, user_sub: str) -> bool:
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub:
            return False
        cur = self._execute(
            _HAS_PAID_BUNDLE_SQL,
            (normalized_sub, self._deployment_environment),
        )
        return cur.fetchone() is not None

    def get_bundle_offer(self) -> BundleOffer | None:
        cur = self._execute(_GET_BUNDLE_OFFER_SQL, (self._deployment_environment,))
        row = cur.fetchone()
        if row is None:
            return None
        amount_minor, currency = row
        return BundleOffer(amount_minor=int(amount_minor), currency=str(currency))

    def set_bundle_price(self, amount_minor: int) -> None:
        if amount_minor <= 0:
            raise ValueError("amount_minor must be positive")
        self._execute(
            _SET_BUNDLE_PRICE_SQL,
            (int(amount_minor), self._deployment_environment),
        )

    def set_course_price(self, course_id: str, amount_minor: int) -> bool:
        normalized_course = (course_id or "").strip()
        if not normalized_course:
            return False
        if amount_minor <= 0:
            raise ValueError("amount_minor must be positive")
        cur = self._execute(
            _SET_COURSE_PRICE_SQL,
            (int(amount_minor), normalized_course),
        )
        return cur.rowcount > 0

    def get_course_price_for_checkout(self, course_id: str) -> dict[str, object] | None:
        normalized_course = (course_id or "").strip()
        if not normalized_course:
            return None
        cur = self._execute(_GET_COURSE_PRICE_SQL, (normalized_course,))
        row = cur.fetchone()
        if row is None:
            return None
        price_minor = row[0]
        if price_minor is None:
            return None
        return {
            "amount_minor": int(price_minor),
            "currency": "USD",
            "course_id": normalized_course,
        }

    def list_purchases_for_user(self, user_sub: str) -> list[PurchaseRecord]:
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub:
            return []
        cur = self._execute(
            _LIST_PURCHASES_FOR_USER_SQL,
            (normalized_sub, self._deployment_environment),
        )
        rows = cur.fetchall() or []
        records: list[PurchaseRecord] = []
        for row in rows:
            pid, product_type, course_id, status, amount_minor, currency, created_at = row
            records.append(
                PurchaseRecord(
                    id=str(pid),
                    product_type=str(product_type),
                    course_id=str(course_id) if course_id is not None else None,
                    status=str(status),
                    amount_minor=int(amount_minor),
                    currency=str(currency),
                    created_at=_as_utc_aware(created_at),
                )
            )
        return records

    def has_checkout_blocking_ownership(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
    ) -> bool:
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub:
            return False
        ptype, cid = self._product_params(product_type, course_id)
        if ptype == "bundle":
            return self.has_paid_bundle(normalized_sub)
        if self.has_paid_bundle(normalized_sub):
            return True
        assert cid is not None
        return self.has_paid_course_purchase(normalized_sub, cid)

    def delete_stale_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
        ttl_minutes: int,
    ) -> None:
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub or ttl_minutes <= 0:
            return
        ptype, cid = self._product_params(product_type, course_id)
        self._execute(
            _DELETE_STALE_PENDING_CHECKOUT_SQL,
            (
                normalized_sub,
                self._deployment_environment,
                ptype,
                cid,
                ttl_minutes,
            ),
        )

    def has_fresh_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
        ttl_minutes: int,
    ) -> bool:
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub or ttl_minutes <= 0:
            return False
        ptype, cid = self._product_params(product_type, course_id)
        cur = self._execute(
            _HAS_FRESH_PENDING_CHECKOUT_SQL,
            (
                normalized_sub,
                self._deployment_environment,
                ptype,
                cid,
                ttl_minutes,
            ),
        )
        return cur.fetchone() is not None

    def delete_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
    ) -> None:
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub:
            return
        ptype, cid = self._product_params(product_type, course_id)
        self._execute(
            _DELETE_PENDING_CHECKOUT_SQL,
            (normalized_sub, self._deployment_environment, ptype, cid),
        )

    def reserve_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
        amount_minor: int,
        currency: str,
        ttl_minutes: int,
        provider: str = "paytabs",
    ) -> tuple[str, str | None]:
        """Atomically supersede stale pending, block fresh pending, or insert pending row.

        Returns ``(status, purchase_id)`` where *status* is ``checkout_in_progress`` or
        ``reserved`` and *purchase_id* is set when a new pending row was inserted.
        """
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub:
            raise ValueError("user_sub is required for pending reservation")
        if amount_minor <= 0:
            raise ValueError("amount_minor must be positive")
        if ttl_minutes <= 0:
            raise ValueError("ttl_minutes must be positive")
        ptype, cid = self._product_params(product_type, course_id)
        conn = self._connection()
        with _atomic_transaction(conn):
            cur = conn.cursor()
            cur.execute(
                _DELETE_STALE_PENDING_CHECKOUT_SQL,
                (
                    normalized_sub,
                    self._deployment_environment,
                    ptype,
                    cid,
                    ttl_minutes,
                ),
            )
            cur.execute(
                _HAS_FRESH_PENDING_CHECKOUT_SQL,
                (
                    normalized_sub,
                    self._deployment_environment,
                    ptype,
                    cid,
                    ttl_minutes,
                ),
            )
            if cur.fetchone() is not None:
                return ("checkout_in_progress", None)
            if ptype == "course":
                assert cid is not None
                cur.execute(
                    _INSERT_PENDING_COURSE_PURCHASE_SQL,
                    (
                        normalized_sub,
                        self._deployment_environment,
                        cid,
                        int(amount_minor),
                        str(currency),
                        provider,
                    ),
                )
            else:
                cur.execute(
                    _INSERT_PENDING_BUNDLE_PURCHASE_SQL,
                    (
                        normalized_sub,
                        self._deployment_environment,
                        int(amount_minor),
                        str(currency),
                        provider,
                    ),
                )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("pending purchase insert did not return id")
            return ("reserved", str(row[0]))
