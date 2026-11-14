"""PostgreSQL idempotent webhook + subscription fulfillment (WS3)."""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

from domain_events import BillingDomainEvent
from fulfillment_config import FulfillmentConfig
from models import PurchaseFulfillmentTarget, purchase_fulfillment_for_event
from db_tx import run_transaction
from service import FulfillmentResult

_USER_SUB_FOR_UPDATE_SQL = """
SELECT user_sub FROM users WHERE user_sub = %s FOR UPDATE
"""

try:  # pragma: no cover - optional until first DB call
    import psycopg2
    from psycopg2 import IntegrityError as Psycopg2IntegrityError
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]
    Psycopg2IntegrityError = Exception  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

def _rds_env_present() -> bool:
    return bool(
        (os.environ.get("DB_HOST") or "").strip()
        or (os.environ.get("DB_SECRET_ARN") or "").strip()
    )


def build_connection_factory(*, dsql_endpoint: str) -> ConnectionFactory:
    endpoint = (dsql_endpoint or "").strip()
    if endpoint and _rds_env_present():
        raise RuntimeError(
            "Configure DSQL_ENDPOINT only for billing fulfillment, not RDS DB_* env vars"
        )
    if not endpoint:
        raise RuntimeError("DSQL_ENDPOINT is required for billing fulfillment")
    from dsql_connect import build_connection_factory as dsql_factory

    return dsql_factory(endpoint)


def _insert_webhook_event(cur: Any, event: BillingDomainEvent) -> Optional[str]:
    cur.execute(
        """
        INSERT INTO payment_webhook_events (
            environment,
            provider,
            provider_event_id,
            event_type,
            payload_digest
        )
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (provider, provider_event_id) DO NOTHING
        RETURNING id::text
        """,
        (
            event.environment,
            event.provider,
            event.provider_event_id,
            event.event_type,
            event.payload_digest,
        ),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])


def _lock_user_row(cur: Any, user_sub: str) -> None:
    cur.execute(_USER_SUB_FOR_UPDATE_SQL, (user_sub,))
    cur.fetchone()


def _select_purchase_for_update(
    cur: Any,
    *,
    event: BillingDomainEvent,
    purchase_id: str,
) -> None:
    """Lock the purchase row. Live webhooks identify it by id; v2 carts also bind user_sub."""
    bound_user = (event.user_sub or "").strip()
    if bound_user:
        cur.execute(
            """
            SELECT amount_minor, currency, status
            FROM purchases
            WHERE id = %s::uuid
              AND user_sub = %s
              AND environment = %s
            FOR UPDATE
            """,
            (purchase_id, bound_user, event.environment),
        )
        return
    cur.execute(
        """
        SELECT amount_minor, currency, status
        FROM purchases
        WHERE id = %s::uuid
          AND environment = %s
        FOR UPDATE
        """,
        (purchase_id, event.environment),
    )


def _apply_purchase_update(cur: Any, *, event: BillingDomainEvent, target: PurchaseFulfillmentTarget) -> bool:
    bound_user = (event.user_sub or "").strip()
    if bound_user:
        _lock_user_row(cur, bound_user)

    if event.event_type in ("purchase.paid", "purchase.failed"):
        _select_purchase_for_update(cur, event=event, purchase_id=target.purchase_id)
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"purchase not found: {target.purchase_id}")
        amount_minor, currency, status = row
        if status != "pending":
            return False
        if event.event_type == "purchase.paid":
            if event.amount_minor is None or not event.currency:
                raise ValueError("purchase.paid IPN must include JOD amount and currency")
        if event.amount_minor is not None and int(amount_minor) != int(event.amount_minor):
            raise ValueError("purchase amount_minor mismatch")
        if event.currency is not None and str(currency).upper() != str(event.currency).upper():
            raise ValueError("purchase currency mismatch")
        cur.execute(
            """
            UPDATE purchases
            SET status = %s,
                provider_tran_ref = COALESCE(%s, provider_tran_ref),
                updated_at = NOW()
            WHERE id = %s::uuid
            """,
            (target.status, target.provider_tran_ref, target.purchase_id),
        )
        return cur.rowcount > 0

    if event.event_type == "purchase.revoked":
        if not bound_user:
            cur.execute(
                """
                UPDATE purchases
                SET status = 'revoked',
                    updated_at = NOW()
                WHERE id = %s::uuid
                  AND environment = %s
                  AND status = 'paid'
                """,
                (target.purchase_id, event.environment),
            )
            return cur.rowcount > 0
        tran_ref = (target.provider_tran_ref or "").strip()
        if not tran_ref:
            raise ValueError("provider_tran_ref is required for purchase.revoked")
        cur.execute(
            """
            UPDATE purchases
            SET status = 'revoked',
                updated_at = NOW()
            WHERE user_sub = %s
              AND environment = %s
              AND provider_tran_ref = %s
              AND status = 'paid'
            """,
            (event.user_sub, event.environment, tran_ref),
        )
        return cur.rowcount > 0

    raise ValueError(f"unsupported purchase event: {event.event_type!r}")


def _mark_webhook_processed(cur: Any, webhook_id: str) -> None:
    cur.execute(
        """
        UPDATE payment_webhook_events
        SET processed_at = NOW()
        WHERE id = %s::uuid
        """,
        (webhook_id,),
    )


def process_event_in_transaction(conn: Any, event: BillingDomainEvent) -> FulfillmentResult:
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")

    def body() -> FulfillmentResult:
        cur = conn.cursor()
        try:
            webhook_id = _insert_webhook_event(cur, event)
            if webhook_id is None:
                return FulfillmentResult(recorded=False, subscription_updated=False)

            purchase_updated = False
            if event.is_purchase_event():
                target = purchase_fulfillment_for_event(event)
                purchase_updated = _apply_purchase_update(cur, event=event, target=target)
            else:
                logger.info(
                    "billing_fulfillment skip non-purchase event_type=%s provider_event_id=%s",
                    event.event_type,
                    event.provider_event_id,
                )

            _mark_webhook_processed(cur, webhook_id)
            return FulfillmentResult(
                recorded=True,
                subscription_updated=False,
                purchase_updated=purchase_updated,
            )
        finally:
            cur.close()

    try:
        return run_transaction(conn, body)
    except Exception as exc:
        if psycopg2 is not None and isinstance(exc, Psycopg2IntegrityError):
            logger.error(
                "billing_fulfillment integrity error user_sub=%s plan_id=%s "
                "provider_event_id=%s",
                event.user_sub,
                event.plan_id,
                event.provider_event_id,
            )
        raise


class RdsFulfillmentRepository:
    """FulfillmentRepository backed by RDS via psycopg2."""

    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory

    def process_event(self, event: BillingDomainEvent) -> FulfillmentResult:
        conn = self._conn_factory()
        try:
            return process_event_in_transaction(conn, event)
        finally:
            conn.close()


_cached_factory: Optional[ConnectionFactory] = None
_cached_repo: Optional[RdsFulfillmentRepository] = None


def get_cached_repository(cfg: FulfillmentConfig) -> RdsFulfillmentRepository:
    global _cached_factory, _cached_repo
    if _cached_repo is None:
        _cached_factory = build_connection_factory(dsql_endpoint=cfg.dsql_endpoint)
        _cached_repo = RdsFulfillmentRepository(_cached_factory)
    return _cached_repo
