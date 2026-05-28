"""Video provider edge environment configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


@dataclass(frozen=True)
class VideoProviderEdgeConfig:
    deployment_environment: str
    catalog_lambda_arn: str | None
    kinescope_api_token: str | None
    kinescope_parent_id: str | None
    kinescope_webhook_secret: str | None
    cors_allow_origin: str | None

    def is_configured(self) -> bool:
        return bool(
            self.catalog_lambda_arn
            and self.kinescope_api_token
            and self.kinescope_parent_id
        )

    def is_webhook_configured(self) -> bool:
        return bool(self.catalog_lambda_arn and self.kinescope_api_token)


def load_video_provider_edge_config() -> VideoProviderEdgeConfig:
    deployment = (_env("DEPLOYMENT_ENVIRONMENT") or "dev").lower()
    return VideoProviderEdgeConfig(
        deployment_environment=deployment,
        catalog_lambda_arn=_env("CATALOG_LAMBDA_ARN"),
        kinescope_api_token=_env("KINESCOPE_API_TOKEN"),
        kinescope_parent_id=_env("KINESCOPE_PARENT_ID"),
        kinescope_webhook_secret=_env("KINESCOPE_WEBHOOK_SECRET"),
        cors_allow_origin=_env("CORS_ALLOW_ORIGIN"),
    )
