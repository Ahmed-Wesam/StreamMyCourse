#!/usr/bin/env python3
"""Apply Aurora DSQL schema files (one DDL/DML statement per transaction)."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CATALOG = _REPO_ROOT / "infrastructure" / "lambda" / "catalog"
if str(_CATALOG) not in sys.path:
    sys.path.insert(0, str(_CATALOG))

from dsql_connect import connect, connection_error  # noqa: E402

DSQL_USER_ADMIN = "admin"
DSQL_ROLE_APP = "smc_app"
DEFAULT_SCHEMA_FILE = _REPO_ROOT / "infrastructure" / "database" / "dsql" / "0001_schema.sql"
MIGRATION_VERSION = "0001"

_ASYNC_INDEX = re.compile(r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+ASYNC", re.IGNORECASE)


def wait_for_async_job(conn: Any, job_id: Any) -> None:
    """``sys.wait_for_job`` must run outside an explicit transaction (autocommit)."""
    previous = conn.autocommit
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CALL sys.wait_for_job(%s)", (job_id,))
    finally:
        conn.autocommit = previous


def split_sql_statements(sql: str) -> list[str]:
    """Split on semicolons; respect single-quoted strings and $$ dollar quotes."""
    lines: list[str] = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    body = "\n".join(lines)

    out: list[str] = []
    buf: list[str] = []
    in_single = False
    in_dollar = False
    i = 0
    while i < len(body):
        ch = body[i]
        if body[i : i + 2] == "$$":
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        if ch == "'" and not in_dollar:
            if in_single and i + 1 < len(body) and body[i + 1] == "'":
                buf.append("''")
                i += 2
                continue
            in_single = not in_single
            buf.append(ch)
            i += 1
            continue
        if ch == ";" and not in_single and not in_dollar:
            piece = "".join(buf).strip()
            if piece:
                out.append(piece + ";")
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1

    piece = "".join(buf).strip()
    if piece:
        out.append(piece)
    return out


def execute_one_statement(conn: Any, sql: str) -> None:
    conn.autocommit = False
    job_id: Any | None = None
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if _ASYNC_INDEX.search(sql) and cur.description:
                row = cur.fetchone()
                if row:
                    job_id = row[0]
        conn.commit()
        if job_id is not None:
            wait_for_async_job(conn, job_id)
    except Exception:
        conn.rollback()
        raise


def apply_statements(conn: Any, statements: Sequence[str]) -> None:
    for sql in statements:
        execute_one_statement(conn, sql)


def migration_already_applied(conn: Any, version: str) -> bool:
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM app.schema_migrations WHERE version = %s",
                (version,),
            )
            return cur.fetchone() is not None
    finally:
        conn.commit()


def apply_migration_file(conn: Any, sql_text: str, version: str) -> bool:
    if migration_already_applied(conn, version):
        return False
    apply_statements(conn, split_sql_statements(sql_text))
    return True


def iam_mapping_exists(conn: Any, role_arn: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM sys.iam_pg_role_mappings
            WHERE iam_role_arn = %s AND pg_role = %s
            """,
            (role_arn, DSQL_ROLE_APP),
        )
        return cur.fetchone() is not None


def apply_iam_grant(conn: Any, role_arn: str) -> None:
    conn.autocommit = False
    try:
        if iam_mapping_exists(conn, role_arn):
            conn.commit()
            return
        with conn.cursor() as cur:
            cur.execute(f"AWS IAM GRANT {DSQL_ROLE_APP} TO '{role_arn}'")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def apply_d3_grants(conn: Any) -> None:
    grants = [
        f"CREATE ROLE {DSQL_ROLE_APP} WITH LOGIN",
        f"GRANT USAGE ON SCHEMA app TO {DSQL_ROLE_APP}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO {DSQL_ROLE_APP}",
        (
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA app "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {DSQL_ROLE_APP}"
        ),
    ]
    for sql in grants:
        try:
            execute_one_statement(conn, sql)
        except Exception as exc:
            if "CREATE ROLE" in sql and "already exists" in str(exc).lower():
                conn.rollback()
                continue
            raise


def apply_schema(
    conn: Any,
    schema_path: Path,
    *,
    version: str,
    iam_role_arns: Sequence[str],
) -> None:
    sql_text = schema_path.read_text(encoding="utf-8")
    apply_migration_file(conn, sql_text, version)
    apply_d3_grants(conn)
    for arn in iam_role_arns:
        arn = arn.strip()
        if arn:
            apply_iam_grant(conn, arn)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply DSQL schema (admin IAM)")
    parser.add_argument(
        "--host",
        default=os.environ.get("DSQL_ENDPOINT", ""),
        help="Cluster endpoint (DSQL_ENDPOINT)",
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=DEFAULT_SCHEMA_FILE,
        help="Path to SQL migration file",
    )
    parser.add_argument(
        "--iam-role-arn",
        action="append",
        default=[],
        dest="iam_role_arns",
        help="Repeatable IAM role ARN for AWS IAM GRANT smc_app",
    )
    parser.add_argument(
        "--version",
        default=MIGRATION_VERSION,
        help="schema_migrations version key",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    host = (args.host or "").strip()
    if not host:
        print("DSQL endpoint host required (DSQL_ENDPOINT or --host)", file=sys.stderr)
        return 2
    if not args.schema_file.is_file():
        print(f"schema file missing: {args.schema_file}", file=sys.stderr)
        return 2

    try:
        conn = connect(DSQL_USER_ADMIN, host)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        apply_schema(
            conn,
            args.schema_file,
            version=args.version,
            iam_role_arns=args.iam_role_arns,
        )
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
