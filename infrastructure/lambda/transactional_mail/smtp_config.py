"""Load Zoho SMTP settings from Secrets Manager (JSON)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import boto3


@dataclass(frozen=True)
class ZohoSmtpConfig:
    host: str
    port: int
    username: str
    password: str
    from_address: str
    reply_to: str


def _parse_secret(raw: str) -> ZohoSmtpConfig:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Zoho SMTP secret must be a JSON object")
    host = str(data.get("smtp_host") or "smtp.zoho.com").strip()
    port_raw = data.get("smtp_port", 587)
    port = int(port_raw)
    username = str(data.get("smtp_username") or "").strip()
    password = str(data.get("smtp_password") or "")
    from_address = str(
        data.get("from_address") or "Research Spectrum <noreply@researchspectrum.org>"
    ).strip()
    reply_to = str(data.get("reply_to") or "support@researchspectrum.org").strip()
    if not username or not password:
        raise ValueError("smtp_username and smtp_password are required in the Zoho secret")
    return ZohoSmtpConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        from_address=from_address,
        reply_to=reply_to,
    )


_secret_cache: ZohoSmtpConfig | None = None


def load_zoho_smtp_config(*, secrets_client: Any | None = None) -> ZohoSmtpConfig:
    global _secret_cache
    if _secret_cache is not None:
        return _secret_cache
    arn = str(os.environ.get("ZOHO_SMTP_SECRET_ARN") or "").strip()
    if not arn:
        raise RuntimeError("ZOHO_SMTP_SECRET_ARN is not configured")
    client = secrets_client or boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=arn)
    raw = resp.get("SecretString") or ""
    if not raw:
        raise ValueError("Zoho SMTP secret has empty SecretString")
    _secret_cache = _parse_secret(raw)
    return _secret_cache
