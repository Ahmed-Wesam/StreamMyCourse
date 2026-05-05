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
    cognito_auth_enabled: bool
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
    # Cognito configuration for JWT verification on public routes
    cognito_user_pool_id: str = ""
    cognito_client_ids: List[str] = None  # type: ignore
    cognito_region: str = ""
    # Progress tracking configuration (lesson completion thresholds)
    progress_complete_ratio: float = 0.92
    progress_position_slack_sec: int = 30

    def __post_init__(self):
        # Ensure cognito_client_ids is a list (frozen dataclass workaround)
        if self.cognito_client_ids is None:
            object.__setattr__(self, "cognito_client_ids", [])


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


def _parse_cognito_pool_arn(arn: str) -> tuple[str, str]:
    """Parse Cognito User Pool ARN to extract (region, pool_id).

    ARN format: arn:aws:cognito-idp:{region}:{account}:userpool/{pool_id}
    Returns ("", "") if the ARN is invalid or empty.
    """
    s = (arn or "").strip()
    if not s:
        return ("", "")
    try:
        # ARN format: arn:aws:cognito-idp:region:account:userpool/pool_id
        parts = s.split(":")
        if len(parts) < 6:
            return ("", "")
        region = parts[3]
        # Last part contains userpool/pool_id
        last_part = parts[-1]
        if "/" not in last_part:
            return ("", "")
        pool_id = last_part.split("/")[-1]
        return (region, pool_id)
    except Exception:
        return ("", "")


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

    cognito_auth_enabled = os.environ.get("COGNITO_AUTH_ENABLED", "").strip().lower() == "true"

    db_host = os.environ.get("DB_HOST", "").strip()
    db_name = os.environ.get("DB_NAME", "").strip()
    db_port = _parse_db_port(os.environ.get("DB_PORT", ""))
    db_secret_arn = os.environ.get("DB_SECRET_ARN", "").strip()

    log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_level = "INFO"

    media_cleanup_queue_url = os.environ.get("MEDIA_CLEANUP_QUEUE_URL", "").strip()

    # Cognito configuration for JWT verification on public routes
    cognito_pool_arn = os.environ.get("COGNITO_USER_POOL_ARN", "").strip()
    cognito_region, cognito_user_pool_id = _parse_cognito_pool_arn(cognito_pool_arn)
    # Client IDs can be comma-separated to support multiple app clients (e.g., student + teacher)
    # For audience validation, we accept any valid client from the pool
    cognito_client_ids = _split_csv(os.environ.get("COGNITO_CLIENT_ID", ""))

    # Progress tracking configuration
    progress_complete_ratio = _parse_float(
        os.environ.get("PROGRESS_COMPLETE_RATIO", "0.92"), 0.92
    )
    progress_position_slack_sec = _parse_int(
        os.environ.get("PROGRESS_POSITION_SLACK_SEC", "30"), 30
    )

    return AppConfig(
        video_bucket=video_bucket,
        default_mp4_url=default_mp4_url,
        video_url=video_url,
        allowed_origins=allowed_origins,
        cognito_auth_enabled=cognito_auth_enabled,
        db_host=db_host,
        db_name=db_name,
        db_port=db_port,
        db_secret_arn=db_secret_arn,
        log_level=log_level,
        media_cleanup_queue_url=media_cleanup_queue_url,
        cognito_user_pool_id=cognito_user_pool_id,
        cognito_client_ids=cognito_client_ids,
        cognito_region=cognito_region,
        progress_complete_ratio=progress_complete_ratio,
        progress_position_slack_sec=progress_position_slack_sec,
    )
