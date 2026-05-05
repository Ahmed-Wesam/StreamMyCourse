from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class AppConfig:
    table_name: str
    video_bucket: str
    default_mp4_url: str
    video_url: str
    allowed_origins: List[str]
    cognito_auth_enabled: bool
    # RDS / PostgreSQL migration fields. Kept optional (defaulted) so existing
    # test fixtures that construct AppConfig with the DynamoDB-only field set
    # keep working; load_config() always fills them in from the environment.
    # use_rds flips the bootstrap between DynamoDB (default; rollback path)
    # and PostgreSQL repos.
    use_rds: bool = False
    db_host: str = ""
    db_name: str = ""
    db_port: int = 5432
    db_secret_arn: str = ""
    # Logging configuration
    log_level: str = "INFO"
    # CloudFront signed URLs for lesson media (optional; empty → S3 presigned GET fallback).
    cloudfront_domain: str = ""
    cloudfront_key_pair_id: str = ""
    cloudfront_private_key_secret_arn: str = ""
    cf_invalidation_lambda_name: str = ""
    # Signed URL / presigned GET lifetime (seconds); default 8 hours.
    media_get_expires_seconds: int = 28800


_DEFAULT_DB_PORT = 5432
_DEFAULT_MEDIA_GET_EXPIRES = 28800


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


def load_config() -> AppConfig:
    table_name = os.environ.get("TABLE_NAME", "").strip()
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

    use_rds = os.environ.get("USE_RDS", "").strip().lower() == "true"
    db_host = os.environ.get("DB_HOST", "").strip()
    db_name = os.environ.get("DB_NAME", "").strip()
    db_port = _parse_db_port(os.environ.get("DB_PORT", ""))
    db_secret_arn = os.environ.get("DB_SECRET_ARN", "").strip()

    log_level = os.environ.get("LOG_LEVEL", "INFO").strip().upper()
    if log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_level = "INFO"

    cloudfront_domain = os.environ.get("CLOUDFRONT_DOMAIN", "").strip()
    cloudfront_key_pair_id = os.environ.get("CLOUDFRONT_KEY_PAIR_ID", "").strip()
    cloudfront_private_key_secret_arn = os.environ.get(
        "CLOUDFRONT_PRIVATE_KEY_SECRET_ARN", ""
    ).strip()
    cf_invalidation_lambda_name = os.environ.get("CF_INVALIDATION_LAMBDA_NAME", "").strip()

    raw_media_ttl = (os.environ.get("MEDIA_GET_EXPIRES_SECONDS") or "").strip()
    if raw_media_ttl:
        try:
            media_get_expires_seconds = max(60, int(raw_media_ttl))
        except ValueError:
            media_get_expires_seconds = _DEFAULT_MEDIA_GET_EXPIRES
    else:
        media_get_expires_seconds = _DEFAULT_MEDIA_GET_EXPIRES

    return AppConfig(
        table_name=table_name,
        video_bucket=video_bucket,
        default_mp4_url=default_mp4_url,
        video_url=video_url,
        allowed_origins=allowed_origins,
        cognito_auth_enabled=cognito_auth_enabled,
        use_rds=use_rds,
        db_host=db_host,
        db_name=db_name,
        db_port=db_port,
        db_secret_arn=db_secret_arn,
        log_level=log_level,
        cloudfront_domain=cloudfront_domain,
        cloudfront_key_pair_id=cloudfront_key_pair_id,
        cloudfront_private_key_secret_arn=cloudfront_private_key_secret_arn,
        cf_invalidation_lambda_name=cf_invalidation_lambda_name,
        media_get_expires_seconds=media_get_expires_seconds,
    )
