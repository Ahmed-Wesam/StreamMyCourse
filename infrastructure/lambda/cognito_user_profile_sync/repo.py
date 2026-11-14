"""PostgreSQL upsert for Cognito-driven user rows.

Duplicates the INSERT ... ON CONFLICT contract from
``UserProfileRdsRepository.put_profile`` in the catalog Lambda so the trigger
stays independent of the ``services/`` package tree. Keep SQL aligned when the
``users`` table contract changes.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable, Optional

try:  # pragma: no cover - optional until first DB call
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Cognito Schema custom attribute names must be <= 20 characters.
COGNITO_STUDENT_SESSION_MIRROR_ATTR = "active_session_id"
COGNITO_STUDENT_SESSION_MIRROR_KEY = f"custom:{COGNITO_STUDENT_SESSION_MIRROR_ATTR}"

ConnectionFactory = Callable[[], Any]


def _cognito_idp_client() -> Any:
    import boto3

    return boto3.client("cognito-idp")


def mirror_student_active_session_attribute(
    *,
    user_pool_id: str,
    user_name: str,
    session_id: str,
) -> None:
    """Mirror RDS session id to ``custom:active_session_id`` on the pool user."""
    if not user_pool_id or not user_name:
        raise ValueError("user_pool_id and user_name are required")
    client = _cognito_idp_client()
    client.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=user_name,
        UserAttributes=[
            {"Name": COGNITO_STUDENT_SESSION_MIRROR_KEY, "Value": session_id},
        ],
    )


def _rds_env_present() -> bool:
    return bool(
        (os.environ.get("DB_HOST") or "").strip()
        or (os.environ.get("DB_SECRET_ARN") or "").strip()
    )


def build_connection_factory(*, dsql_endpoint: str) -> ConnectionFactory:
    endpoint = (dsql_endpoint or "").strip()
    if endpoint and _rds_env_present():
        raise RuntimeError(
            "Configure DSQL_ENDPOINT only for user profile sync, not RDS DB_* env vars"
        )
    if not endpoint:
        raise RuntimeError("DSQL_ENDPOINT is required for user profile sync")
    from dsql_connect import build_connection_factory as dsql_factory

    return dsql_factory(endpoint)


_PROFILE_COLUMNS = "user_sub, email, role, cognito_sub, created_at, updated_at"


def get_student_active_session_id(conn_factory: ConnectionFactory, *, user_sub: str) -> str:
    """Return RDS ``student_active_session_id`` for ``user_sub`` (empty when missing)."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")
    conn = conn_factory()
    cur = conn.cursor()
    cur.execute(
        "SELECT student_active_session_id FROM users WHERE user_sub = %s",
        (user_sub,),
    )
    row = cur.fetchone()
    if not row:
        return ""
    return str(row[0] or "")


def set_student_active_session_id(
    conn_factory: ConnectionFactory, *, user_sub: str, session_id: str
) -> None:
    """Persist the canonical student session id (upsert row if needed)."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")
    from db_tx import run_transaction

    conn = conn_factory()

    def body() -> None:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (user_sub, email, role, cognito_sub, student_active_session_id, last_login_at)
            VALUES (%s, '', 'student', %s, %s, NOW())
            ON CONFLICT (user_sub) DO UPDATE
              SET student_active_session_id = EXCLUDED.student_active_session_id,
                  last_login_at = NOW(),
                  updated_at = NOW()
            """,
            (user_sub, user_sub, session_id),
        )

    run_transaction(conn, body)


def upsert_user_profile(
    conn_factory: ConnectionFactory,
    *,
    user_sub: str,
    email: str,
    role: str,
    student_active_session_id: str | None = None,
) -> None:
    """Idempotent UPSERT into ``users`` (same semantics as catalog ``put_profile``)."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")
    from db_tx import run_transaction

    conn = conn_factory()

    def body() -> None:
            cur = conn.cursor()
            if student_active_session_id is not None:
                cur.execute(
                    f"""
                    INSERT INTO users (user_sub, email, role, cognito_sub, student_active_session_id)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_sub) DO UPDATE
                      SET email       = EXCLUDED.email,
                          role        = EXCLUDED.role,
                          cognito_sub = EXCLUDED.cognito_sub,
                          student_active_session_id = EXCLUDED.student_active_session_id,
                          updated_at  = NOW()
                    RETURNING {_PROFILE_COLUMNS}
                    """,
                    (user_sub, email, role, user_sub, student_active_session_id),
                )
            else:
                cur.execute(
                    f"""
                    INSERT INTO users (user_sub, email, role, cognito_sub)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_sub) DO UPDATE
                      SET email       = EXCLUDED.email,
                          role        = EXCLUDED.role,
                          cognito_sub = EXCLUDED.cognito_sub,
                          updated_at  = NOW()
                    RETURNING {_PROFILE_COLUMNS}
                    """,
                    (user_sub, email, role, user_sub),
                )
            row = cur.fetchone()
            if row is None:
                logger.warning("users upsert returned no row for sub_prefix=%s", user_sub[:8])

    run_transaction(conn, body)


_cached_factory: Optional[ConnectionFactory] = None


def get_cached_connection_factory(cfg: Any) -> ConnectionFactory:
    """Return a process-wide connection factory (one Secrets Manager fetch per warm container)."""
    global _cached_factory
    if _cached_factory is None:
        _cached_factory = build_connection_factory(dsql_endpoint=cfg.dsql_endpoint)
    return _cached_factory
