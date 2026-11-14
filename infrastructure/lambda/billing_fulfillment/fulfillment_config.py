"""Environment-driven configuration for billing fulfillment Lambda."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FulfillmentConfig:
    deployment_environment: str
    dsql_endpoint: str = ""


def load_fulfillment_config() -> FulfillmentConfig:
    return FulfillmentConfig(
        deployment_environment=os.environ.get("DEPLOYMENT_ENVIRONMENT", "").strip(),
        dsql_endpoint=os.environ.get("DSQL_ENDPOINT", "").strip(),
    )
