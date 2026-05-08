"""VPC Lambda: apply bundled PostgreSQL DDL to RDS using Secrets Manager credentials.

Invoked by CI after the RDS stack is ready; the runner calls ``lambda:Invoke`` (no
VPC reachability to port 5432 required). Idempotent: ``CREATE ... IF NOT EXISTS``."""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import boto3
import psycopg2
from botocore.exceptions import ClientError


class JsonLogFormatter(logging.Formatter):
    """JSON formatter for structured logging (duplicated from catalog Lambda)."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_obj["exc_info"] = self._format_exception(record.exc_info)

        # JSON encode with proper escaping
        return json.dumps(log_obj, ensure_ascii=False, default=str)

    def _format_timestamp(self, created: float) -> str:
        """Format timestamp as ISO 8601 UTC."""
        dt = datetime.fromtimestamp(created, tz=timezone.utc)
        return dt.isoformat()

    def _format_exception(self, exc_info: tuple) -> str:
        """Format exception info as string."""
        return "".join(traceback.format_exception(*exc_info))


def _configure_logging() -> None:
    """Configure JSON logging from LOG_LEVEL env var."""
    log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add JSON handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(handler)

    if log_level == logging.DEBUG:
        root_logger.warning("DEBUG logging enabled - verify no sensitive data in production")


# Configure logging on module load
_configure_logging()
logger = logging.getLogger(__name__)


def _split_sql_statements(sql: str) -> list[str]:
    """Split DDL on semicolons, respecting $$ dollar-quoted blocks.

    Strips full-line SQL comments first, then scans character-by-character so
    that semicolons inside $$ ... $$ blocks (e.g. DO $$ ... $$; PL/pgSQL) are
    not treated as statement terminators.  Only plain $$ quoting is supported;
    named dollar-quotes ($tag$...$tag$) are not required by our migrations.
    """
    lines: list[str] = []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        lines.append(line)
    body = "\n".join(lines)

    out: list[str] = []
    buf: list[str] = []
    in_dollar_quote = False
    i = 0
    while i < len(body):
        if body[i : i + 2] == "$$":
            in_dollar_quote = not in_dollar_quote
            buf.append("$$")
            i += 2
            continue
        if body[i] == ";" and not in_dollar_quote:
            piece = "".join(buf).strip()
            if piece:
                out.append(piece + ";")
            buf = []
            i += 1
            continue
        buf.append(body[i])
        i += 1

    # Flush any trailing non-terminated content (no-op for well-formed SQL).
    piece = "".join(buf).strip()
    if piece:
        out.append(piece)

    return out


def handler(event, context):
    lambda_request_id = getattr(context, "aws_request_id", "")
    logger.info(
        "Invoke request",
        extra={
            "lambda_request_id": lambda_request_id,
            "action": "rds_schema_apply",
        },
    )
    if event:
        logger.debug("event keys: %s", list(event) if isinstance(event, dict) else type(event))
    secret_arn = os.environ.get("SECRET_ARN", "").strip()
    if not secret_arn:
        logger.error("SECRET_ARN is not set")
        return {"ok": False, "error": "SECRET_ARN is not set"}

    schema_path = Path(__file__).resolve().parent / "schema.sql"
    if not schema_path.is_file():
        logger.error("schema.sql missing", extra={"schema_path": str(schema_path)})
        return {"ok": False, "error": f"schema.sql missing at {schema_path}"}
    sql = schema_path.read_text(encoding="utf-8")

    conn = None
    try:
        sm = boto3.client("secretsmanager")
        raw = sm.get_secret_value(SecretId=secret_arn)["SecretString"]
        data = json.loads(raw)
        conn = psycopg2.connect(
            host=data["host"],
            port=int(data.get("port", 5432)),
            user=data["username"],
            password=data["password"],
            dbname=data["dbname"],
            sslmode="require",
            connect_timeout=30,
        )
        conn.autocommit = False
        statements = _split_sql_statements(sql)
        total = len(statements)
        with conn.cursor() as cur:
            # Fail fast on lock contention instead of consuming the full Lambda
            # timeout silently. ALTER TABLE statements in migrations need
            # AccessExclusiveLock; if a long-running idle-in-transaction
            # connection (e.g. the catalog Lambda's persistent connection) holds
            # AccessShareLock, the apply hangs until the Lambda runtime kills
            # the process. Failing in 30s with a clear `lock_timeout` error
            # gives the operator a clean signal and a stack trace identifying
            # which statement was blocked.
            cur.execute("SET lock_timeout = '30s'")
            for i, stmt in enumerate(statements, start=1):
                # Do not log statement text — future migrations could include literals.
                logger.info(
                    "Executing DDL statement",
                    extra={
                        "statement_number": i,
                        "total_statements": total,
                        "action": "rds_schema_apply",
                    },
                )
                cur.execute(stmt)
        conn.commit()
        logger.info(
            "Schema apply completed",
            extra={
                "total_statements": total,
                "action": "rds_schema_apply",
            },
        )
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
        logger.exception("Schema apply failed", extra={"action": "rds_schema_apply"})
        return {"ok": False, "error": str(e)}
    finally:
        if conn is not None:
            conn.close()

    return {"ok": True}
