"""PostgreSQL idempotent webhook + subscription fulfillment (WS3)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from domain_events import BillingDomainEvent
from fulfillment_config import FulfillmentConfig
from models import SubscriptionUpdate, subscription_update_for_event
from service import FulfillmentResult

try:  # pragma: no cover - optional until first DB call
    import psycopg2
    from psycopg2 import IntegrityError as Psycopg2IntegrityError
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]
    Psycopg2IntegrityError = Exception  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_GRANTING_STATUSES = ("active", "past_due", "incomplete")


def _secretsmanager_client() -> Any:
    import boto3

    return boto3.client("secretsmanager")


def _psycopg2_connect(**kwargs: Any) -> Any:
    import psycopg2 as pg

    return pg.connect(**kwargs)


def build_connection_factory(
    *,
    db_secret_arn: str,
    db_host: str,
    db_name: str,
    db_port: int,
) -> ConnectionFactory:
    if not db_secret_arn:
        raise RuntimeError("DB_SECRET_ARN is required")
    if not db_host:
        raise RuntimeError("DB_HOST is required")

    def factory() -> Any:
        sm = _secretsmanager_client()
        response = sm.get_secret_value(SecretId=db_secret_arn)
        payload_raw = response.get("SecretString") or ""
        try:
            payload = json.loads(payload_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("RDS secret is not valid JSON") from exc
        user = str(payload.get("username") or "")
        password = str(payload.get("password") or "")
        if not user or not password:
            raise RuntimeError("RDS secret missing username/password fields")
        return _psycopg2_connect(
            host=db_host,
            port=int(db_port or 5432),
            dbname=db_name,
            user=user,
            password=password,
            sslmode="require",
            connect_timeout=5,
        )

    return factory


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


def _find_subscription_row_id(cur: Any, *, user_sub: str, environment: str) -> Optional[str]:
    cur.execute(
        """
        SELECT id::text
        FROM user_subscriptions
        WHERE user_sub = %s
          AND environment = %s
          AND status = ANY(%s)
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (user_sub, environment, list(_GRANTING_STATUSES)),
    )
    row = cur.fetchone()
    if row is not None:
        return str(row[0])

    cur.execute(
        """
        SELECT id::text
        FROM user_subscriptions
        WHERE user_sub = %s
          AND environment = %s
        ORDER BY updated_at DESC
        LIMIT 1
        """,
        (user_sub, environment),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return str(row[0])


def _apply_subscription_update(
    cur: Any,
    *,
    event: BillingDomainEvent,
    update: SubscriptionUpdate,
) -> None:
    row_id = _find_subscription_row_id(
        cur, user_sub=event.user_sub, environment=event.environment
    )
    if row_id is not None:
        cur.execute(
            """
            UPDATE user_subscriptions
            SET plan_id = %s,
                provider = %s,
                provider_subscription_id = COALESCE(%s, provider_subscription_id),
                status = %s,
                current_period_start = COALESCE(%s::timestamptz, current_period_start),
                current_period_end = COALESCE(%s::timestamptz, current_period_end),
                cancel_at_period_end = %s,
                canceled_at = %s::timestamptz,
                updated_at = NOW()
            WHERE id = %s::uuid
            """,
            (
                update.plan_id,
                update.provider,
                update.provider_subscription_id,
                update.status,
                update.current_period_start,
                update.current_period_end,
                update.cancel_at_period_end,
                update.canceled_at,
                row_id,
            ),
        )
        return

    cur.execute(
        """
        INSERT INTO user_subscriptions (
            user_sub,
            environment,
            plan_id,
            provider,
            provider_subscription_id,
            status,
            current_period_start,
            current_period_end,
            cancel_at_period_end,
            canceled_at
        )
        VALUES (%s, %s, %s::uuid, %s, %s, %s, %s::timestamptz, %s::timestamptz, %s, %s::timestamptz)
        """,
        (
            event.user_sub,
            event.environment,
            update.plan_id,
            update.provider,
            update.provider_subscription_id,
            update.status,
            update.current_period_start,
            update.current_period_end,
            update.cancel_at_period_end,
            update.canceled_at,
        ),
    )


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

    cur = conn.cursor()
    try:
        webhook_id = _insert_webhook_event(cur, event)
        if webhook_id is None:
            conn.commit()
            return FulfillmentResult(recorded=False, subscription_updated=False)

        subscription_updated = False
        if event.is_subscription_event():
            update = subscription_update_for_event(event)
            _apply_subscription_update(cur, event=event, update=update)
            subscription_updated = True
        else:
            logger.info(
                "billing_fulfillment skip subscription for event_type=%s provider_event_id=%s",
                event.event_type,
                event.provider_event_id,
            )

        _mark_webhook_processed(cur, webhook_id)
        conn.commit()
        return FulfillmentResult(recorded=True, subscription_updated=subscription_updated)
    except Exception as exc:
        conn.rollback()
        if psycopg2 is not None and isinstance(exc, Psycopg2IntegrityError):
            logger.error(
                "billing_fulfillment integrity error user_sub=%s plan_id=%s "
                "provider_event_id=%s",
                event.user_sub,
                event.plan_id,
                event.provider_event_id,
            )
        raise
    finally:
        cur.close()


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
        _cached_factory = build_connection_factory(
            db_secret_arn=cfg.db_secret_arn,
            db_host=cfg.db_host,
            db_name=cfg.db_name,
            db_port=cfg.db_port,
        )
        _cached_repo = RdsFulfillmentRepository(_cached_factory)
    return _cached_repo
