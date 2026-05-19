from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class AppConfig:
    video_bucket: str
    default_mp4_url: str
    video_url: str
    allowed_origins: List[str]
    # RDS / PostgreSQL (catalog + progress). Incomplete values mean the handler
    # returns catalog_unconfigured until the api stack wires DB_* from the RDS stack.
    db_host: str = ""
    db_name: str = ""
    db_port: int = 5432
    db_secret_arn: str = ""
    # Logging configuration
    log_level: str = "INFO"
    # Optional SQS queue URL for async S3 cleanup after course delete (empty = legacy sync delete)
    media_cleanup_queue_url: str = ""
    # Progress tracking configuration (lesson completion thresholds)
    progress_complete_ratio: float = 0.92
    progress_position_slack_sec: int = 30
    # Billing (merchant status teacher gate + RDS environment key)
    billing_teacher_sub: str = ""
    deployment_environment: str = "dev"

_DEFAULT_DB_PORT = 5432


def _split_csv(raw: str) -> List[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]


def _parse_db_port(raw: str) -> int:
    """Parse DB_PORT, falling back to 5432 on missing/invalid input.

    We deliberately do not raise at cold start -- a bad value (e.g. an
    unresolved CloudFormation ImportValue placeholder during a rollback) should
    fail at first connection attempt, not at handler import time.
    """
    s = (raw or "").strip()
    if not s:
        return _DEFAULT_DB_PORT
    try:
        return int(s)
    except ValueError:
        return _DEFAULT_DB_PORT


def _parse_float(val: str, default: float) -> float:
    """Parse a float value, falling back to default on invalid input.

    Used for configuration values that should have sensible defaults
    rather than failing at cold start.
    """
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_int(val: str, default: int) -> int:
    """Parse an int value, falling back to default on invalid input.

    Used for configuration values that should have sensible defaults
    rather than failing at cold start.
    """
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def load_config() -> AppConfig:
    video_bucket = os.environ.get("VIDEO_BUCKET", "").strip()
    default_mp4_url = os.environ.get(
        "DEFAULT_MP4_URL",
        "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4",
    ).strip()
    video_url = os.environ.get("VIDEO_URL", "").strip()

    raw_origins = os.environ.get("ALLOWED_ORIGINS", "").strip()
    # Fail-secure: no implicit wildcard. Use ALLOWED_ORIGINS=* explicitly for dev/tools.
    allowed_origins = _split_csv(raw_origins) if raw_origins else []

    db_host = os.environ.get("DB_HOST", "").strip()
    db_name = os.environ.get("DB_NAME", "").strip()
    db_port = _parse_db_port(os.environ.get("DB_PORT", ""))
    db_secret_arn = os.environ.get("DB_SECRET_ARN", "").strip()

    log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_level = "INFO"

    media_cleanup_queue_url = os.environ.get("MEDIA_CLEANUP_QUEUE_URL", "").strip()

    # Progress tracking configuration
    progress_complete_ratio = _parse_float(
        os.environ.get("PROGRESS_COMPLETE_RATIO", "0.92"), 0.92
    )
    progress_position_slack_sec = _parse_int(
        os.environ.get("PROGRESS_POSITION_SLACK_SEC", "30"), 30
    )

    billing_teacher_sub = os.environ.get("BILLING_TEACHER_SUB", "").strip()
    deployment_raw = os.environ.get("DEPLOYMENT_ENVIRONMENT", "").strip()
    deployment_environment = (deployment_raw or "dev").lower()

    return AppConfig(
        video_bucket=video_bucket,
        default_mp4_url=default_mp4_url,
        video_url=video_url,
        allowed_origins=allowed_origins,
        db_host=db_host,
        db_name=db_name,
        db_port=db_port,
        db_secret_arn=db_secret_arn,
        log_level=log_level,
        media_cleanup_queue_url=media_cleanup_queue_url,
        progress_complete_ratio=progress_complete_ratio,
        progress_position_slack_sec=progress_position_slack_sec,
        billing_teacher_sub=billing_teacher_sub,
        deployment_environment=deployment_environment,
    )
