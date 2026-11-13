"""Aurora DSQL admin SQL helper for integration tests (S7 foundation gate)."""

from __future__ import annotations

import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CATALOG = _REPO_ROOT / "infrastructure" / "lambda" / "catalog"
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_CATALOG) not in sys.path:
    sys.path.insert(0, str(_CATALOG))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dsql_connect import connect  # noqa: E402
from dsql_orphan_audit import fk_orphan_counts  # noqa: E402
from services.common.db_tx import run_transaction  # noqa: E402

DSQL_USER_ADMIN = "admin"
DSQL_STACK_OUTPUT = "StreamMyCourse-Dsql-prod"
_DEFAULT_REGION = "eu-west-1"


def resolve_dsql_endpoint() -> str:
    """Cluster hostname from ``DSQL_ENDPOINT`` or CloudFormation output."""
    host = os.environ.get("DSQL_ENDPOINT", "").strip()
    if host:
        return host
    region = os.environ.get("INTEGRATION_AWS_REGION", _DEFAULT_REGION).strip() or _DEFAULT_REGION
    try:
        import boto3

        cf = boto3.client("cloudformation", region_name=region)
        resp = cf.describe_stacks(StackName=DSQL_STACK_OUTPUT)
        for out in resp["Stacks"][0].get("Outputs", []):
            if out.get("OutputKey") == "Endpoint":
                value = (out.get("OutputValue") or "").strip()
                if value:
                    return value
    except Exception:
        pass
    return ""


def admin_connection():
    """Open an admin IAM connection; caller must close."""
    host = resolve_dsql_endpoint()
    if not host:
        raise RuntimeError(
            "DSQL endpoint not configured (set DSQL_ENDPOINT or deploy StreamMyCourse-Dsql-prod)"
        )
    return connect(DSQL_USER_ADMIN, host)


@contextmanager
def admin_connect() -> Iterator[Any]:
    """Context manager yielding an admin connection."""
    conn = admin_connection()
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def execute_scalar(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def run_orphan_audit_script() -> subprocess.CompletedProcess[str]:
    """Run ``scripts/dsql_orphan_audit.py``; never logs tokens (script uses IAM only)."""
    host = resolve_dsql_endpoint()
    env = {**os.environ}
    if host:
        env["DSQL_ENDPOINT"] = host
    return subprocess.run(
        [sys.executable, str(_SCRIPTS / "dsql_orphan_audit.py"), "--host", host],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


__all__ = [
    "admin_connect",
    "admin_connection",
    "execute_scalar",
    "fk_orphan_counts",
    "resolve_dsql_endpoint",
    "run_orphan_audit_script",
    "run_transaction",
]
