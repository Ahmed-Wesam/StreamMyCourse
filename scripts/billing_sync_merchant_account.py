#!/usr/bin/env python3
"""Upsert ``teacher_merchant_accounts`` from deploy-time env (W4-P4).

Requires RDS reachability from the runner (``DB_HOST`` + ``DB_SECRET_ARN``).
When the database is unreachable (typical CI), exits 0 with a skip message.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Tuple

try:
    import psycopg2
except Exception:  # pragma: no cover - optional until connect
    psycopg2 = None  # type: ignore[assignment]

DEFAULT_PROVIDER = "paytabs"


@dataclass(frozen=True)
class MerchantSyncParams:
    environment: str
    teacher_sub: str
    provider_profile_id: Optional[str]
    provider: str = DEFAULT_PROVIDER


def build_upsert_sql() -> str:
    """UPSERT by ``environment``; do not reset ``payout_ready`` on conflict."""
    return """
        INSERT INTO teacher_merchant_accounts (
            environment,
            teacher_sub,
            provider,
            provider_profile_id
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (environment) DO UPDATE SET
            teacher_sub = EXCLUDED.teacher_sub,
            provider_profile_id = EXCLUDED.provider_profile_id,
            updated_at = NOW()
        """.strip()


def merge_params_from_env(environ: Optional[Mapping[str, str]] = None) -> MerchantSyncParams:
    """Merge ``DEPLOYMENT_ENVIRONMENT``, ``BILLING_TEACHER_SUB``, ``PAYTABS_PROFILE_ID``."""
    raw = os.environ if environ is None else environ
    environment = str(raw.get("DEPLOYMENT_ENVIRONMENT", "")).strip()
    teacher_sub = str(raw.get("BILLING_TEACHER_SUB", "")).strip()
    profile_id = str(raw.get("PAYTABS_PROFILE_ID", "")).strip()
    if not environment:
        raise ValueError("DEPLOYMENT_ENVIRONMENT is required")
    if not teacher_sub:
        raise ValueError("BILLING_TEACHER_SUB is required")
    return MerchantSyncParams(
        environment=environment,
        teacher_sub=teacher_sub,
        provider_profile_id=profile_id or None,
    )


def upsert_params_tuple(params: MerchantSyncParams) -> Tuple[Any, ...]:
    return (
        params.environment,
        params.teacher_sub,
        params.provider,
        params.provider_profile_id,
    )


def run_upsert(conn: Any, params: MerchantSyncParams) -> None:
    cur = conn.cursor()
    cur.execute(build_upsert_sql(), upsert_params_tuple(params))
    conn.commit()


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


def _load_db_config(environ: Mapping[str, str]) -> Tuple[str, str, str, int]:
    host = str(environ.get("DB_HOST", "")).strip()
    secret_arn = str(environ.get("DB_SECRET_ARN", "")).strip()
    db_name = str(environ.get("DB_NAME", "streammycourse")).strip() or "streammycourse"
    port_raw = str(environ.get("DB_PORT", "5432")).strip() or "5432"
    return host, secret_arn, db_name, int(port_raw)


def main(argv: Optional[list[str]] = None) -> int:
    _ = argv
    try:
        params = merge_params_from_env()
    except ValueError as exc:
        print(f"billing_sync_merchant_account: {exc}", file=sys.stderr)
        return 1

    host, secret_arn, db_name, db_port = _load_db_config(os.environ)
    if not host or not secret_arn:
        print(
            "billing_sync_merchant_account: DB_HOST/DB_SECRET_ARN unset; "
            "skipping merchant sync (RDS not configured on runner)"
        )
        return 0

    try:
        factory = build_connection_factory(
            db_secret_arn=secret_arn,
            db_host=host,
            db_name=db_name,
            db_port=db_port,
        )
        conn = factory()
    except Exception as exc:
        if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
            print(
                f"billing_sync_merchant_account: RDS unreachable ({exc}); skipping merchant sync"
            )
            return 0
        print(f"billing_sync_merchant_account: connect failed: {exc}", file=sys.stderr)
        return 1

    try:
        run_upsert(conn, params)
        print(
            f"billing_sync_merchant_account: upserted teacher_merchant_accounts "
            f"for environment={params.environment}"
        )
        return 0
    except Exception as exc:
        if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
            print(
                f"billing_sync_merchant_account: RDS unreachable during upsert ({exc}); "
                "skipping merchant sync"
            )
            return 0
        print(f"billing_sync_merchant_account: upsert failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
