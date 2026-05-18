"""Load PayTabs credentials from Secrets Manager (prod SM-only path)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE: dict[str, "PaytabsCredentials"] = {}


@dataclass(frozen=True)
class PaytabsCredentials:
    server_key: str
    profile_id: str
    api_domain: str | None


def load_paytabs_from_secret(secret_id: str) -> Optional[PaytabsCredentials]:
    """Fetch JSON secret {server_key, profile_id, api_domain?} by ARN or secret name."""
    key = (secret_id or "").strip()
    if not key:
        return None
    if key in _CACHE:
        return _CACHE[key]

    try:
        import boto3
    except ImportError:
        logger.warning("boto3 unavailable; cannot load PayTabs secret")
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
        server_key = str(data.get("server_key") or "").strip()
        profile_id = str(data.get("profile_id") or "").strip()
        api_domain = str(data.get("api_domain") or "").strip() or None
        if not server_key or not profile_id:
            return None
        creds = PaytabsCredentials(
            server_key=server_key,
            profile_id=profile_id,
            api_domain=api_domain,
        )
        _CACHE[key] = creds
        return creds
    except Exception:
        logger.exception("Failed to load PayTabs secret (id redacted)")
        return None


def clear_paytabs_secret_cache() -> None:
    """Test helper."""
    _CACHE.clear()
