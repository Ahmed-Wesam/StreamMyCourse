"""Load HyperPay credentials from Secrets Manager (prod SM-only path)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE: dict[str, "HyperpayCredentials"] = {}


@dataclass(frozen=True)
class HyperpayCredentials:
    access_token: str
    entity_id: str
    webhook_secret: str | None = None
    api_host: str | None = None


def load_hyperpay_from_secret(secret_id: str) -> Optional[HyperpayCredentials]:
    """Fetch JSON secret {access_token, entity_id, webhook_secret?, api_host?}."""
    key = (secret_id or "").strip()
    if not key:
        return None
    if key in _CACHE:
        return _CACHE[key]

    try:
        import boto3
    except ImportError:
        logger.warning("boto3 unavailable; cannot load HyperPay secret")
        return None

    try:
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=key)
        raw = response.get("SecretString") or ""
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        access_token = str(data.get("access_token") or "").strip()
        entity_id = str(data.get("entity_id") or "").strip()
        webhook_secret = str(data.get("webhook_secret") or "").strip() or None
        api_host = str(data.get("api_host") or "").strip() or None
        if not access_token or not entity_id:
            return None
        creds = HyperpayCredentials(
            access_token=access_token,
            entity_id=entity_id,
            webhook_secret=webhook_secret,
            api_host=api_host,
        )
        _CACHE[key] = creds
        return creds
    except Exception:
        logger.exception("Failed to load HyperPay secret (id redacted)")
        return None


def clear_hyperpay_secret_cache() -> None:
    """Test helper."""
    _CACHE.clear()
