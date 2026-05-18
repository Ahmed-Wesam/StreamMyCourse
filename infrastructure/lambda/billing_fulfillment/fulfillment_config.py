"""Environment-driven configuration for billing fulfillment Lambda."""

from __future__ import annotations

import os
from dataclasses import dataclass

_DEFAULT_DB_PORT = 5432


@dataclass(frozen=True)
class FulfillmentConfig:
    deployment_environment: str
    db_secret_arn: str
    db_host: str
    db_name: str
    db_port: int


def _parse_db_port(raw: str) -> int:
    s = (raw or "").strip()
    if not s:
        return _DEFAULT_DB_PORT
    try:
        return int(s)
    except ValueError:
        return _DEFAULT_DB_PORT


def load_fulfillment_config() -> FulfillmentConfig:
    return FulfillmentConfig(
        deployment_environment=os.environ.get("DEPLOYMENT_ENVIRONMENT", "").strip(),
        db_secret_arn=os.environ.get("DB_SECRET_ARN", "").strip(),
        db_host=os.environ.get("DB_HOST", "").strip(),
        db_name=os.environ.get("DB_NAME", "postgres").strip() or "postgres",
        db_port=_parse_db_port(os.environ.get("DB_PORT", "")),
    )
