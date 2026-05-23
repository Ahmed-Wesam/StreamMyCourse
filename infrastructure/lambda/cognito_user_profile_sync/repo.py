"""PostgreSQL upsert for Cognito-driven user rows.

Duplicates the INSERT ... ON CONFLICT contract from
``UserProfileRdsRepository.put_profile`` in the catalog Lambda so the trigger
stays independent of the ``services/`` package tree. Keep SQL aligned when the
``users`` table contract changes.
"""

from __future__ import annotations

import json
import logging
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


def _secretsmanager_client() -> Any:
    import boto3

    return boto3.client("secretsmanager")


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


def _psycopg2_connect(**kwargs: Any) -> Any:
    import psycopg2 as pg

    return pg.connect(**kwargs)


def build_connection_factory(*, db_secret_arn: str, db_host: str, db_name: str, db_port: int) -> ConnectionFactory:
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


_PROFILE_COLUMNS = "user_sub, email, role, cognito_sub, created_at, updated_at"


def get_student_active_session_id(conn_factory: ConnectionFactory, *, user_sub: str) -> str:
    """Return RDS ``student_active_session_id`` for ``user_sub`` (empty when missing)."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")
    conn = conn_factory()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT student_active_session_id FROM users WHERE user_sub = %s",
            (user_sub,),
        )
        row = cur.fetchone()
        if not row:
            return ""
        return str(row[0] or "")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def set_student_active_session_id(
    conn_factory: ConnectionFactory, *, user_sub: str, session_id: str
) -> None:
    """Persist the canonical student session id (upsert row if needed)."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")
    conn = conn_factory()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (user_sub, email, role, cognito_sub, student_active_session_id)
            VALUES (%s, '', 'student', %s, %s)
            ON CONFLICT (user_sub) DO UPDATE
              SET student_active_session_id = EXCLUDED.student_active_session_id,
                  updated_at = NOW()
            """,
            (user_sub, user_sub, session_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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
    conn = conn_factory()
    try:
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
        conn.commit()
        row = cur.fetchone()
        if row is None:
            logger.warning("users upsert returned no row for sub_prefix=%s", user_sub[:8])
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_cached_factory: Optional[ConnectionFactory] = None


def get_cached_connection_factory(cfg: Any) -> ConnectionFactory:
    """Return a process-wide connection factory (one Secrets Manager fetch per warm container)."""
    global _cached_factory
    if _cached_factory is None:
        _cached_factory = build_connection_factory(
            db_secret_arn=cfg.db_secret_arn,
            db_host=cfg.db_host,
            db_name=cfg.db_name,
            db_port=cfg.db_port,
        )
    return _cached_factory
