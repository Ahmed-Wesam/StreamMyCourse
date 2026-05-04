"""Cognito PostAuthentication trigger: upsert ``users`` row in RDS (idempotent)."""

from __future__ import annotations

import _vendor_bootstrap  # noqa: F401  # must precede repo -> psycopg2

import logging
from typing import Any, Dict

from repo import get_cached_connection_factory, upsert_user_profile
from sync_config import SyncConfig, load_sync_config

logger = logging.getLogger(__name__)
_LOG_PREFIX = "cognito_user_profile_sync"

# Test hook: patch in unit tests to avoid config / DB wiring.
_config_loader = load_sync_config


def _normalize_role(raw: str) -> str:
    """Match ``UserProfileService.get_or_create_profile`` role normalization."""
    normalized_role = (raw or "student").strip().lower()
    if normalized_role not in ("student", "teacher", "admin"):
        normalized_role = "student"
    return normalized_role


def sync_post_authentication(event: Dict[str, Any], cfg: SyncConfig) -> Dict[str, Any]:
    """Parse Cognito PostAuthentication event and upsert RDS user; never raises."""
    request = event.get("request") if isinstance(event.get("request"), dict) else {}
    raw_attrs = request.get("userAttributes")
    attrs: Dict[str, str] = {}
    if isinstance(raw_attrs, dict):
        attrs = {str(k): str(v) if v is not None else "" for k, v in raw_attrs.items()}

    user_sub = str(attrs.get("sub", "") or "").strip()
    email = str(attrs.get("email", "") or "").strip()
    role_raw = str(attrs.get("custom:role") or attrs.get("role") or "student").strip()
    role = _normalize_role(role_raw)

    if not user_sub:
        logger.warning("%s missing sub in userAttributes; passing event through", _LOG_PREFIX)
        return event

    if not cfg.db_secret_arn or not cfg.db_host:
        logger.warning(
            "%s misconfigured (DB_SECRET_ARN / DB_HOST); passing event through",
            _LOG_PREFIX,
        )
        return event

    try:
        factory = get_cached_connection_factory(cfg)
        upsert_user_profile(factory, user_sub=user_sub, email=email, role=role)
        logger.info(
            "%s upserted user",
            _LOG_PREFIX,
            extra={"user_sub_prefix": user_sub[:8]},
        )
    except Exception:
        # Do not block login on DB or edge failures; monitor CloudWatch instead.
        logger.exception(
            "%s failed; allowing authentication to continue",
            _LOG_PREFIX,
            extra={"user_sub_prefix": user_sub[:8]},
        )
    return event


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda entry point for Cognito PostAuthentication."""
    logging.getLogger().setLevel(logging.INFO)
    cfg = _config_loader()
    return sync_post_authentication(event, cfg)
