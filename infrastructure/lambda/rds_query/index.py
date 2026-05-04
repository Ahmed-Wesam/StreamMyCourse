"""In-VPC Lambda: ad-hoc read SQL, gated mutating SQL, or catalog wipe (operator only).

Invoke via ``aws lambda invoke`` (no API Gateway). ``confirm`` must match
``EXPECTED_ENVIRONMENT``. Catalog wipe requires ``wipe_catalog`` and
``ALLOW_CATALOG_WIPE``. Mutating ``sql`` requires ``allow_mutating_sql`` and
``ALLOW_MUTATING_SQL``. ``wipe_catalog`` and ``sql`` are mutually exclusive."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Sequence, Tuple

import boto3
import psycopg2
from botocore.exceptions import ClientError

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), stream=sys.stdout)
logger = logging.getLogger(__name__)

_CATALOG_TABLES = ("enrollments", "lessons", "courses", "users")
_TRUNCATE_SQL = (
    "TRUNCATE enrollments, lessons, courses, users RESTART IDENTITY CASCADE;"
)
_STATEMENT_TIMEOUT_MS = 60_000
_MAX_ROWS = 2000

# Heuristic: detect DML/DDL smuggled inside CTEs or after SELECT (not a full SQL parser).
_MUTATING_CLAUSE_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE | re.DOTALL)
    for p in (
        r"\bDELETE\s+FROM\b",
        r"\bINSERT\s+INTO\b",
        r"\bTRUNCATE\b",
        r"\bMERGE\s+",
        r"\bDROP\s+(TABLE|INDEX|SCHEMA|DATABASE|VIEW|SEQUENCE|EXTENSION)\b",
        r"\bALTER\s+(TABLE|INDEX|SCHEMA|DATABASE|VIEW|SEQUENCE|EXTENSION|ROLE)\b",
        r"\bCREATE\s+(TABLE|INDEX|EXTENSION|FUNCTION|TRIGGER|VIEW|SCHEMA|DATABASE)\b",
        r"\bGRANT\b",
        r"\bREVOKE\b",
        r"\bUPDATE\s+\S+\s+SET\b",
        r"\bSELECT\b.{0,12000}?\bINTO\b",
    )
)


def sql_contains_mutating_clause(sql: str) -> bool:
    """True if sql text matches common mutating DML/DDL patterns (case-insensitive)."""
    return any(p.search(sql) for p in _MUTATING_CLAUSE_PATTERNS)


def _parse_event(event: Any) -> Dict[str, Any]:
    if event is None:
        return {}
    if isinstance(event, str):
        try:
            return json.loads(event)
        except json.JSONDecodeError:
            return {}
    if isinstance(event, dict):
        return event
    return {}


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return False


def _leading_sql_text(sql: str) -> str:
    """Join non-empty, non-full-line-comment lines for token detection."""
    parts: List[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        parts.append(stripped)
    return " ".join(parts)


def sql_looks_read_only(sql: str) -> bool:
    """Heuristic: first significant token is SELECT / WITH / EXPLAIN / SHOW / TABLE."""
    head = _leading_sql_text(sql)
    if not head:
        return False
    token_match = re.match(r"^([A-Za-z_]+)", head)
    if not token_match:
        return False
    token = token_match.group(1).upper()
    return token in ("SELECT", "WITH", "EXPLAIN", "SHOW", "TABLE")


def _sql_statement_parts(sql: str) -> List[str]:
    return [p.strip() for p in sql.split(";") if p.strip()]


def _counts(cur) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for table in _CATALOG_TABLES:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        out[table] = int(cur.fetchone()[0])
    return out


def _rows_payload(
    cur: Any, rows: Sequence[Tuple[Any, ...]]
) -> Tuple[List[Dict[str, Any]], bool]:
    if not cur.description:
        return [], False
    colnames = [d[0] for d in cur.description]
    out: List[Dict[str, Any]] = []
    truncated = len(rows) > _MAX_ROWS
    for row in rows[:_MAX_ROWS]:
        out.append({colnames[i]: row[i] for i in range(len(colnames))})
    return out, truncated


def _connect_from_secret(secret_arn: str) -> Any:
    sm = boto3.client("secretsmanager")
    raw = sm.get_secret_value(SecretId=secret_arn)["SecretString"]
    data = json.loads(raw)
    return psycopg2.connect(
        host=data["host"],
        port=int(data.get("port", 5432)),
        user=data["username"],
        password=data["password"],
        dbname=data["dbname"],
        sslmode="require",
        connect_timeout=30,
    )


def handler(event: Any, _context: Any) -> Dict[str, Any]:
    expected = (os.environ.get("EXPECTED_ENVIRONMENT") or "").strip()
    if not expected:
        return {"ok": False, "error": "EXPECTED_ENVIRONMENT is not set"}

    payload = _parse_event(event)
    confirm = str(payload.get("confirm", "")).strip()
    if confirm != expected:
        return {
            "ok": False,
            "error": "confirm payload must match stack environment",
            "expected": expected,
            "got": confirm,
        }

    secret_arn = (os.environ.get("SECRET_ARN") or "").strip()
    if not secret_arn:
        return {"ok": False, "error": "SECRET_ARN is not set"}

    wipe_catalog = _coerce_bool(payload.get("wipe_catalog"))
    sql_raw = payload.get("sql")
    sql = str(sql_raw).strip() if sql_raw is not None else ""

    if wipe_catalog and sql:
        return {
            "ok": False,
            "error": "wipe_catalog and sql are mutually exclusive",
        }

    if not wipe_catalog and not sql:
        return {
            "ok": False,
            "error": "provide wipe_catalog true or a non-empty sql string",
        }

    if wipe_catalog:
        if not _truthy_env("ALLOW_CATALOG_WIPE"):
            return {
                "ok": False,
                "error": "wipe_catalog requires ALLOW_CATALOG_WIPE=true on the function",
            }
        return _run_wipe(secret_arn, expected)

    parts = _sql_statement_parts(sql)
    if len(parts) > 1:
        return {"ok": False, "error": "multiple SQL statements are not allowed"}

    is_read = sql_looks_read_only(sql)
    if is_read and sql_contains_mutating_clause(sql):
        return {
            "ok": False,
            "error": (
                "sql contains DML/DDL patterns not allowed on the read path; "
                "use allow_mutating_sql with ALLOW_MUTATING_SQL or rewrite the query"
            ),
        }

    allow_mut_payload = _coerce_bool(payload.get("allow_mutating_sql"))
    if not is_read and (
        not allow_mut_payload or not _truthy_env("ALLOW_MUTATING_SQL")
    ):
        return {
            "ok": False,
            "error": "mutating sql requires allow_mutating_sql in payload and "
            "ALLOW_MUTATING_SQL=true on the function",
        }

    if is_read:
        return _run_read_sql(secret_arn, sql, expected)
    return _run_mutating_sql(secret_arn, sql, expected)


def _run_wipe(secret_arn: str, environment: str) -> Dict[str, Any]:
    conn = None
    try:
        conn = _connect_from_secret(secret_arn)
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (_STATEMENT_TIMEOUT_MS,))
            counts_before = _counts(cur)
            cur.execute(_TRUNCATE_SQL)
            counts_after = _counts(cur)
        conn.commit()
        logger.info(
            "rds_query wipe_catalog completed",
            extra={"environment": environment, "sql_len": len(_TRUNCATE_SQL)},
        )
        return {
            "ok": True,
            "mode": "wipe_catalog",
            "environment": environment,
            "counts_before": counts_before,
            "counts_after": counts_after,
        }
    except (
        psycopg2.Error,
        ClientError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as e:
        if conn is not None:
            conn.rollback()
        logger.exception("rds_query wipe_catalog failed")
        return {"ok": False, "error": str(e)}
    finally:
        if conn is not None:
            conn.close()


def _run_read_sql(secret_arn: str, sql: str, environment: str) -> Dict[str, Any]:
    conn = None
    try:
        conn = _connect_from_secret(secret_arn)
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (_STATEMENT_TIMEOUT_MS,))
            cur.execute(sql)
            if cur.description is None:
                conn.commit()
                return {
                    "ok": True,
                    "mode": "read",
                    "environment": environment,
                    "rows": [],
                    "truncated": False,
                }
            rows = cur.fetchmany(_MAX_ROWS + 1)
            payload, truncated = _rows_payload(cur, rows)
        conn.commit()
        logger.info(
            "rds_query read completed",
            extra={
                "environment": environment,
                "sql_len": len(sql),
                "row_count": len(payload),
                "truncated": truncated,
            },
        )
        return {
            "ok": True,
            "mode": "read",
            "environment": environment,
            "rows": payload,
            "truncated": truncated,
        }
    except (
        psycopg2.Error,
        ClientError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as e:
        if conn is not None:
            conn.rollback()
        logger.exception("rds_query read failed")
        return {"ok": False, "error": str(e)}
    finally:
        if conn is not None:
            conn.close()


def _run_mutating_sql(secret_arn: str, sql: str, environment: str) -> Dict[str, Any]:
    conn = None
    try:
        conn = _connect_from_secret(secret_arn)
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = %s", (_STATEMENT_TIMEOUT_MS,))
            cur.execute(sql)
            rc = cur.rowcount
        conn.commit()
        logger.info(
            "rds_query mutating completed",
            extra={"environment": environment, "sql_len": len(sql)},
        )
        return {
            "ok": True,
            "mode": "mutating",
            "environment": environment,
            "rowcount": rc,
        }
    except (
        psycopg2.Error,
        ClientError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as e:
        if conn is not None:
            conn.rollback()
        logger.exception("rds_query mutating failed")
        return {"ok": False, "error": str(e)}
    finally:
        if conn is not None:
            conn.close()
