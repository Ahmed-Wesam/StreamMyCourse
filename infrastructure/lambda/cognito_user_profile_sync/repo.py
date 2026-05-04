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

ConnectionFactory = Callable[[], Any]


def _secretsmanager_client() -> Any:
    import boto3

    return boto3.client("secretsmanager")


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


def upsert_user_profile(conn_factory: ConnectionFactory, *, user_sub: str, email: str, role: str) -> None:
    """Idempotent UPSERT into ``users`` (same semantics as catalog ``put_profile``)."""
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is not available")
    conn = conn_factory()
    try:
        cur = conn.cursor()
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
