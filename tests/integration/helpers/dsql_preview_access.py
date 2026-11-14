"""DSQL admin purchase rows for integration tests (no payments edge required)."""

from __future__ import annotations

import os
import uuid

from helpers.dsql_audit import admin_connect, execute_scalar

_DEFAULT_BUNDLE_FILS = 150_000


def _billing_environment() -> str:
    return os.environ.get("INTEGRATION_BILLING_ENV", "prod").strip() or "prod"


def _bundle_amount_minor(conn) -> int:
    env = _billing_environment()
    row = execute_scalar(
        conn,
        "SELECT amount_minor FROM app.bundle_offers WHERE environment = %s LIMIT 1",
        (env,),
    )
    if row is not None:
        return int(row)
    return _DEFAULT_BUNDLE_FILS


def insert_paid_course_purchase(
    user_sub: str,
    course_id: str,
    *,
    purchase_id: str | None = None,
    amount_minor: int = 1000,
) -> str:
    """Admin INSERT of a paid course row. Returns purchase id."""
    pid = purchase_id or str(uuid.uuid4())
    env = _billing_environment()
    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.purchases (
                    id, user_sub, environment, product_type, course_id,
                    status, amount_minor, currency
                ) VALUES (%s, %s, %s, 'course', %s, 'paid', %s, 'JOD')
                """,
                (pid, user_sub, env, course_id, amount_minor),
            )
        conn.commit()
    return pid


def insert_paid_bundle_purchase(user_sub: str, *, purchase_id: str | None = None) -> str:
    """Admin INSERT of a paid bundle row. Returns purchase id."""
    pid = purchase_id or str(uuid.uuid4())
    env = _billing_environment()
    with admin_connect() as conn:
        amount_minor = _bundle_amount_minor(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.purchases (
                    id, user_sub, environment, product_type, course_id,
                    status, amount_minor, currency
                ) VALUES (%s, %s, %s, 'bundle', NULL, 'paid', %s, 'JOD')
                """,
                (pid, user_sub, env, amount_minor),
            )
        conn.commit()
    return pid


def delete_purchase_by_id(purchase_id: str) -> None:
    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM app.purchases WHERE id = %s", (purchase_id,))
        conn.commit()


def delete_purchases_for_course_id(course_id: str) -> None:
    """Remove purchase rows referencing *course_id* (integration cleanup only)."""
    cid = (course_id or "").strip()
    try:
        uuid.UUID(cid)
    except ValueError as e:
        raise ValueError(f"refusing non-UUID course_id: {course_id!r}") from e
    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM app.purchases WHERE course_id = %s", (cid,))
        conn.commit()