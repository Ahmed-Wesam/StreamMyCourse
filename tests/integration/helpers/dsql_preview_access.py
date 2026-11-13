"""DSQL-4 D9: preview-stack student access without the payments edge."""

from __future__ import annotations

import os
import uuid

from helpers.api import ApiClient
from helpers.dsql_audit import admin_connect, execute_scalar


def _billing_environment() -> str:
    return os.environ.get("INTEGRATION_BILLING_ENV", "prod").strip() or "prod"

_DEFAULT_BUNDLE_FILS = 150_000


def is_dsql_preview_api_stack() -> bool:
    """True when integration tests target the preview API (``*Api-dsql``)."""
    return os.environ.get("INTEGRATION_API_STACK", "").strip().endswith("Api-dsql")


def ensure_student_profile_row(student_api: ApiClient) -> None:
    """``GET /users/me`` so Cognito-triggered profile exists on DSQL before FK inserts."""
    resp = student_api.get_users_me()
    assert resp.status_code == 200, f"GET /users/me failed: status={resp.status_code}"


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


def insert_paid_bundle_purchase(user_sub: str, *, purchase_id: str | None = None) -> str:
    """Admin INSERT of a paid bundle row (preview only). Returns purchase id."""
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


def grant_preview_bundle_access(_student_api: ApiClient, user_sub: str) -> str | None:
    """Ensure a paid bundle purchase exists for ``user_sub`` on preview; returns new purchase id or None."""
    env = _billing_environment()
    with admin_connect() as conn:
        existing = execute_scalar(
            conn,
            """
            SELECT id FROM app.purchases
            WHERE user_sub = %s AND environment = %s
              AND product_type = 'bundle' AND status = 'paid'
            LIMIT 1
            """,
            (user_sub, env),
        )
        if existing:
            return None
    return insert_paid_bundle_purchase(user_sub)
