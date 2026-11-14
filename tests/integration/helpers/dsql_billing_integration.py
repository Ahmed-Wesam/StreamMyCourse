"""DSQL-5 S6: shared billing integration helpers (no secrets logged)."""

from __future__ import annotations

import uuid

from helpers.billing_access import billing_environment
from helpers.dsql_audit import admin_connect, execute_scalar


def count_purchases_for_user(user_sub: str) -> int:
    with admin_connect() as conn:
        return int(
            execute_scalar(
                conn,
                "SELECT COUNT(*) FROM app.purchases WHERE user_sub = %s",
                (user_sub,),
            )
            or 0
        )


def count_pending_bundle_checkouts(user_sub: str) -> int:
    env = billing_environment()
    with admin_connect() as conn:
        return int(
            execute_scalar(
                conn,
                """
                SELECT COUNT(*) FROM app.purchases
                WHERE user_sub = %s AND environment = %s
                  AND product_type = 'bundle' AND status = 'pending'
                """,
                (user_sub, env),
            )
            or 0
        )


def insert_pending_bundle_purchase(
    user_sub: str,
    *,
    amount_minor: int | None = None,
    purchase_id: str | None = None,
) -> str:
    pid = purchase_id or str(uuid.uuid4())
    env = billing_environment()
    with admin_connect() as conn:
        if amount_minor is None:
            row = execute_scalar(
                conn,
                "SELECT amount_minor FROM app.bundle_offers WHERE environment = %s LIMIT 1",
                (env,),
            )
            amount_minor = int(row or 150_000)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.purchases (
                    id, user_sub, environment, product_type, course_id,
                    status, amount_minor, currency
                ) VALUES (%s, %s, %s, 'bundle', NULL, 'pending', %s, 'JOD')
                """,
                (pid, user_sub, env, amount_minor),
            )
        conn.commit()
    return pid


def delete_webhook_events(provider: str, provider_event_ids: list[str]) -> None:
    if not provider_event_ids:
        return
    with admin_connect() as conn:
        with conn.cursor() as cur:
            for eid in provider_event_ids:
                cur.execute(
                    "DELETE FROM app.payment_webhook_events WHERE provider = %s AND provider_event_id = %s",
                    (provider, eid),
                )
        conn.commit()