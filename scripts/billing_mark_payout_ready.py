#!/usr/bin/env python3
"""Set ``teacher_merchant_accounts.payout_ready`` for teacher checklist UI (WS4 F1).

Does **not** affect student checkout. Requires RDS reachability from the runner.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from billing_sync_merchant_account import (  # noqa: E402
    _load_db_config,
    build_connection_factory,
)


def build_mark_payout_ready_sql() -> str:
    return """
        UPDATE teacher_merchant_accounts
        SET payout_ready = TRUE,
            payout_ready_at = NOW(),
            updated_at = NOW()
        WHERE environment = %s
        """.strip()


def run_mark_payout_ready(conn: Any, environment: str) -> int:
    cur = conn.cursor()
    cur.execute(build_mark_payout_ready_sql(), (environment,))
    updated = cur.rowcount
    conn.commit()
    return int(updated)


def main(argv: Optional[list[str]] = None) -> int:
    _ = argv
    environment = str(os.environ.get("DEPLOYMENT_ENVIRONMENT", "")).strip()
    if not environment:
        print("billing_mark_payout_ready: DEPLOYMENT_ENVIRONMENT is required", file=sys.stderr)
        return 1

    host, secret_arn, db_name, db_port = _load_db_config(os.environ)
    if not host or not secret_arn:
        print(
            "billing_mark_payout_ready: DB_HOST/DB_SECRET_ARN unset; "
            "skipping (RDS not configured on runner)"
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
            print(f"billing_mark_payout_ready: RDS unreachable ({exc}); skipping")
            return 0
        print(f"billing_mark_payout_ready: connect failed: {exc}", file=sys.stderr)
        return 1

    try:
        updated = run_mark_payout_ready(conn, environment)
        if updated == 0:
            print(
                f"billing_mark_payout_ready: no row for environment={environment}; "
                "run billing-sync-merchant-account first"
            )
            return 1
        print(
            f"billing_mark_payout_ready: payout_ready=true for environment={environment}"
        )
        return 0
    except Exception as exc:
        if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
            print(f"billing_mark_payout_ready: RDS unreachable during update ({exc}); skipping")
            return 0
        print(f"billing_mark_payout_ready: update failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
