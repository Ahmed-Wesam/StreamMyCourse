#!/usr/bin/env python3
"""One-shot DynamoDB -> RDS PostgreSQL data migration.

Run this **after** the rds-stack is deployed and the initial SQL schema has
been applied, and **before** flipping ``USE_RDS=true`` on the Lambda. Designed
to be idempotent via ``ON CONFLICT DO NOTHING`` -- re-running it is safe and
acts as a catch-up pass for any DynamoDB rows that were created between the
first run and the cutover.

Usage::

    export AWS_REGION=eu-west-1
    export DYNAMODB_TABLE=StreamMyCourse-Catalog-dev
    export DB_SECRET_ARN=arn:aws:secretsmanager:...:secret:streammycourse/dev/rds-credentials-xxxxxx
    export DB_HOST=streammycourse-dev.xxxxxx.rds.amazonaws.com
    export DB_PORT=5432
    export DB_NAME=streammycourse

    python scripts/migrate-dynamodb-to-rds.py --dry-run
    python scripts/migrate-dynamodb-to-rds.py

Exit codes:
    0  -- success
    1  -- configuration error or AWS failure
    2  -- data integrity error (e.g. UUID parsing)

**IMPORTANT:** This script talks to DynamoDB and RDS directly. Run it from an
operator workstation or a one-off EC2/Fargate task *inside the RDS VPC*. Use
temporary credentials (STS assume-role) scoped to the migration; do not run
from CI.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import boto3
from boto3.dynamodb.conditions import Attr
import psycopg2
import psycopg2.extras


logger = logging.getLogger("migrate-dynamodb-to-rds")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class MigrationConfig:
    region: str
    dynamodb_table: str
    db_host: str
    db_port: int
    db_name: str
    db_secret_arn: str
    dry_run: bool
    batch_size: int

    @classmethod
    def from_env(cls, args: argparse.Namespace) -> "MigrationConfig":
        region = os.environ.get("AWS_REGION", "eu-west-1")
        table = os.environ.get("DYNAMODB_TABLE", "").strip()
        host = os.environ.get("DB_HOST", "").strip()
        port = int(os.environ.get("DB_PORT", "5432") or 5432)
        dbname = os.environ.get("DB_NAME", "").strip()
        secret_arn = os.environ.get("DB_SECRET_ARN", "").strip()
        missing = [
            name
            for name, value in (
                ("DYNAMODB_TABLE", table),
                ("DB_HOST", host),
                ("DB_NAME", dbname),
                ("DB_SECRET_ARN", secret_arn),
            )
            if not value
        ]
        if missing:
            logger.error("Missing required environment variables: %s", ", ".join(missing))
            sys.exit(1)
        return cls(
            region=region,
            dynamodb_table=table,
            db_host=host,
            db_port=port,
            db_name=dbname,
            db_secret_arn=secret_arn,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def _get_rds_connection(cfg: MigrationConfig):
    sm = boto3.client("secretsmanager", region_name=cfg.region)
    secret = json.loads(sm.get_secret_value(SecretId=cfg.db_secret_arn)["SecretString"])
    return psycopg2.connect(
        host=cfg.db_host,
        port=cfg.db_port,
        dbname=cfg.db_name,
        user=secret["username"],
        password=secret["password"],
        sslmode="require",
        connect_timeout=10,
    )


def _get_ddb_table(cfg: MigrationConfig):
    return boto3.resource("dynamodb", region_name=cfg.region).Table(cfg.dynamodb_table)


def _scan_all(table, **scan_kwargs) -> Iterable[Dict[str, Any]]:
    """Yield every item matching the scan, transparently following pagination."""
    last_key: Optional[Dict[str, Any]] = None
    while True:
        if last_key is not None:
            scan_kwargs["ExclusiveStartKey"] = last_key
        response = table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            yield item
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break


# ---------------------------------------------------------------------------
# Domain extractors
# ---------------------------------------------------------------------------


def _iso_or_now(raw: Any) -> datetime:
    s = str(raw or "").strip()
    if not s:
        return datetime.now(timezone.utc)
    try:
        # DynamoDB rows store ISO strings via `datetime.now(...).isoformat()`.
        return datetime.fromisoformat(s)
    except ValueError:
        logger.warning("Bad timestamp %r; using NOW()", s)
        return datetime.now(timezone.utc)


def _strip_prefix(raw: Any, prefix: str) -> str:
    return str(raw or "").replace(prefix, "", 1)


def _iter_courses(table) -> Iterable[Dict[str, Any]]:
    # PK starts_with COURSE# AND SK = METADATA
    return _scan_all(
        table,
        FilterExpression=Attr("PK").begins_with("COURSE#") & Attr("SK").eq("METADATA"),
    )


def _iter_lessons(table) -> Iterable[Dict[str, Any]]:
    return _scan_all(
        table,
        FilterExpression=Attr("PK").begins_with("COURSE#") & Attr("SK").begins_with("LESSON#"),
    )


def _iter_users(table) -> Iterable[Dict[str, Any]]:
    return _scan_all(
        table,
        FilterExpression=Attr("PK").begins_with("USER#") & Attr("SK").eq("METADATA"),
    )


def _iter_enrollments(table) -> Iterable[Dict[str, Any]]:
    return _scan_all(
        table,
        FilterExpression=Attr("PK").begins_with("USER#") & Attr("SK").begins_with("ENROLLMENT#"),
    )


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------


def migrate_users(cur, table, cfg: MigrationConfig) -> Tuple[int, int]:
    """Migrate user profiles first -- enrollments FK references users.user_sub."""
    inserted = skipped = 0
    rows: List[Tuple[Any, ...]] = []
    for item in _iter_users(table):
        user_sub = _strip_prefix(item.get("PK"), "USER#")
        if not user_sub:
            skipped += 1
            continue
        rows.append(
            (
                user_sub,
                str(item.get("email") or ""),
                str(item.get("role") or "student"),
                str(item.get("cognitoSub") or user_sub),
                _iso_or_now(item.get("createdAt")),
                _iso_or_now(item.get("updatedAt")),
            )
        )
        if len(rows) >= cfg.batch_size:
            inserted += _flush_users(cur, rows, cfg)
            rows = []
    if rows:
        inserted += _flush_users(cur, rows, cfg)
    logger.info("users: inserted=%d skipped=%d", inserted, skipped)
    return inserted, skipped


def _flush_users(cur, rows: List[Tuple[Any, ...]], cfg: MigrationConfig) -> int:
    if cfg.dry_run:
        logger.info("[dry-run] would insert %d users", len(rows))
        return len(rows)
    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO users (user_sub, email, role, cognito_sub, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_sub) DO NOTHING
        """,
        rows,
    )
    return len(rows)


def migrate_courses(cur, table, cfg: MigrationConfig) -> Tuple[int, int]:
    inserted = skipped = 0
    rows: List[Tuple[Any, ...]] = []
    for item in _iter_courses(table):
        course_id = _strip_prefix(item.get("PK"), "COURSE#")
        if not course_id:
            skipped += 1
            continue
        rows.append(
            (
                course_id,
                str(item.get("title") or "Untitled"),
                str(item.get("description") or ""),
                str(item.get("status") or "DRAFT"),
                str(item.get("createdBy") or ""),
                str(item.get("thumbnailKey") or ""),
                _iso_or_now(item.get("createdAt")),
                _iso_or_now(item.get("updatedAt")),
            )
        )
        if len(rows) >= cfg.batch_size:
            inserted += _flush_courses(cur, rows, cfg)
            rows = []
    if rows:
        inserted += _flush_courses(cur, rows, cfg)
    logger.info("courses: inserted=%d skipped=%d", inserted, skipped)
    return inserted, skipped


def _flush_courses(cur, rows: List[Tuple[Any, ...]], cfg: MigrationConfig) -> int:
    if cfg.dry_run:
        logger.info("[dry-run] would insert %d courses", len(rows))
        return len(rows)
    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO courses (id, title, description, status, created_by, thumbnail_key, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        rows,
    )
    return len(rows)


def migrate_lessons(cur, table, cfg: MigrationConfig) -> Tuple[int, int]:
    inserted = skipped = 0
    rows: List[Tuple[Any, ...]] = []
    for item in _iter_lessons(table):
        course_id = _strip_prefix(item.get("PK"), "COURSE#")
        lesson_id = str(item.get("lessonId") or "").strip()
        order_raw = item.get("order")
        # Legacy rows used SK=LESSON#<int> as order. Fall back to that only
        # when the explicit `order` field is missing.
        if order_raw is None:
            sk = str(item.get("SK") or "")
            sk_suffix = sk.replace("LESSON#", "")
            order_val = int(sk_suffix) if sk_suffix.isdigit() else 0
        else:
            order_val = int(order_raw or 0)
        if not course_id or not lesson_id:
            skipped += 1
            continue
        rows.append(
            (
                lesson_id,
                course_id,
                str(item.get("title") or ""),
                order_val,
                str(item.get("videoKey") or ""),
                str(item.get("videoStatus") or "pending"),
                str(item.get("thumbnailKey") or ""),
                int(item.get("duration") or 0),
            )
        )
        if len(rows) >= cfg.batch_size:
            inserted += _flush_lessons(cur, rows, cfg)
            rows = []
    if rows:
        inserted += _flush_lessons(cur, rows, cfg)
    logger.info("lessons: inserted=%d skipped=%d", inserted, skipped)
    return inserted, skipped


def _flush_lessons(cur, rows: List[Tuple[Any, ...]], cfg: MigrationConfig) -> int:
    if cfg.dry_run:
        logger.info("[dry-run] would insert %d lessons", len(rows))
        return len(rows)
    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO lessons (id, course_id, title, lesson_order, video_key, video_status, thumbnail_key, duration)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        rows,
    )
    return len(rows)


def migrate_enrollments(cur, table, cfg: MigrationConfig) -> Tuple[int, int]:
    inserted = skipped = 0
    rows: List[Tuple[Any, ...]] = []
    for item in _iter_enrollments(table):
        user_sub = _strip_prefix(item.get("PK"), "USER#")
        course_id = _strip_prefix(item.get("SK"), "ENROLLMENT#")
        if not user_sub or not course_id:
            skipped += 1
            continue
        rows.append(
            (
                user_sub,
                course_id,
                _iso_or_now(item.get("enrolledAt")),
                str(item.get("source") or "self_service"),
            )
        )
        if len(rows) >= cfg.batch_size:
            inserted += _flush_enrollments(cur, rows, cfg)
            rows = []
    if rows:
        inserted += _flush_enrollments(cur, rows, cfg)
    logger.info("enrollments: inserted=%d skipped=%d", inserted, skipped)
    return inserted, skipped


def _flush_enrollments(cur, rows: List[Tuple[Any, ...]], cfg: MigrationConfig) -> int:
    if cfg.dry_run:
        logger.info("[dry-run] would insert %d enrollments", len(rows))
        return len(rows)
    psycopg2.extras.execute_batch(
        cur,
        """
        INSERT INTO enrollments (user_sub, course_id, enrolled_at, source)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_sub, course_id) DO NOTHING
        """,
        rows,
    )
    return len(rows)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan DynamoDB and count rows but do not write to RDS",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Rows per psycopg2.execute_batch call (default 100)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=args.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = MigrationConfig.from_env(args)

    logger.info(
        "Starting migration table=%s host=%s dry_run=%s",
        cfg.dynamodb_table,
        cfg.db_host,
        cfg.dry_run,
    )
    ddb_table = _get_ddb_table(cfg)
    conn = _get_rds_connection(cfg)
    try:
        with conn:  # commit/rollback per successful migration pass
            with conn.cursor() as cur:
                # users must land before enrollments (FK constraint).
                migrate_users(cur, ddb_table, cfg)
                migrate_courses(cur, ddb_table, cfg)
                migrate_lessons(cur, ddb_table, cfg)
                migrate_enrollments(cur, ddb_table, cfg)
    finally:
        conn.close()

    logger.info("Migration complete (dry_run=%s)", cfg.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
