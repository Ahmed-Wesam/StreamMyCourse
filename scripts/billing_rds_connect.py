"""Shared RDS connection helpers for billing operator scripts."""

from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Optional, Tuple

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]


def _secretsmanager_client() -> Any:
    import boto3

    return boto3.client("secretsmanager")


def build_connection_factory(
    *,
    db_secret_arn: str,
    db_host: str,
    db_name: str,
    db_port: int,
    secrets_client: Optional[Any] = None,
    connect_fn: Optional[Callable[..., Any]] = None,
) -> Callable[[], Any]:
    if not db_secret_arn:
        raise RuntimeError("DB_SECRET_ARN is required")
    if not db_host:
        raise RuntimeError("DB_HOST is required")

    def factory() -> Any:
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not available")
        sm = secrets_client if secrets_client is not None else _secretsmanager_client()
        response = sm.get_secret_value(SecretId=db_secret_arn)
        payload_raw = response.get("SecretString") or ""
        payload = json.loads(payload_raw)
        user = str(payload.get("username") or "")
        password = str(payload.get("password") or "")
        if not user or not password:
            raise RuntimeError("RDS secret missing username/password fields")
        connect = connect_fn if connect_fn is not None else psycopg2.connect
        return connect(
            host=db_host,
            port=int(db_port or 5432),
            dbname=db_name,
            user=user,
            password=password,
            sslmode="require",
            connect_timeout=5,
        )

    return factory


def load_db_config(environ: Mapping[str, str]) -> Tuple[str, str, str, int]:
    host = str(environ.get("DB_HOST", "")).strip()
    secret_arn = str(environ.get("DB_SECRET_ARN", "")).strip()
    db_name = str(environ.get("DB_NAME", "streammycourse")).strip() or "streammycourse"
    port_raw = str(environ.get("DB_PORT", "5432")).strip() or "5432"
    return host, secret_arn, db_name, int(port_raw)
