"""Billing edge environment configuration and provider factory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from hyperpay_secrets import load_hyperpay_from_secret
from providers.hyperpay_adapter import HyperPayAdapter
from providers.mock_adapter import MockHyperPayAdapter
from providers.port import PaymentProviderPort

_DEFAULT_API_HOST = "eu-test.oppwa.com"


def _env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


@dataclass(frozen=True)
class BillingEdgeConfig:
    deployment_environment: str
    payment_provider: str | None
    hyperpay_secret_arn: str | None
    hyperpay_access_token: str | None
    hyperpay_entity_id: str | None
    hyperpay_webhook_secret: str | None
    fulfillment_queue_url: str | None
    catalog_lambda_arn: str | None
    billing_shopper_result_url: str | None

    def is_prod(self) -> bool:
        return self.deployment_environment.lower() == "prod"

    def wants_mock(self) -> bool:
        return (self.payment_provider or "").lower() == "mock"

    def has_hyperpay_inline_keys(self) -> bool:
        return bool(self.hyperpay_access_token and self.hyperpay_entity_id)

    def has_hyperpay_secret_arn(self) -> bool:
        return bool(self.hyperpay_secret_arn)

    def is_configured(self) -> bool:
        return get_payment_provider(self) is not None


def load_billing_edge_config() -> BillingEdgeConfig:
    deployment = (_env("DEPLOYMENT_ENVIRONMENT") or "prod").lower()
    return BillingEdgeConfig(
        deployment_environment=deployment,
        payment_provider=_env("PAYMENT_PROVIDER"),
        hyperpay_secret_arn=_env("HYPERPAY_SECRET_ARN"),
        hyperpay_access_token=_env("HYPERPAY_ACCESS_TOKEN"),
        hyperpay_entity_id=_env("HYPERPAY_ENTITY_ID"),
        hyperpay_webhook_secret=_env("HYPERPAY_WEBHOOK_SECRET"),
        fulfillment_queue_url=_env("FULFILLMENT_QUEUE_URL"),
        catalog_lambda_arn=_env("CATALOG_LAMBDA_ARN"),
        billing_shopper_result_url=_env("BILLING_SHOPPER_RESULT_URL"),
    )


def resolve_hyperpay_credentials(
    cfg: BillingEdgeConfig,
) -> tuple[str, str, str | None, str | None] | None:
    """Inline env first, then Secrets Manager when HYPERPAY_SECRET_ARN is set."""
    access_token = cfg.hyperpay_access_token or ""
    entity_id = cfg.hyperpay_entity_id or ""
    webhook_secret = cfg.hyperpay_webhook_secret
    api_host = _DEFAULT_API_HOST

    if access_token and entity_id:
        return access_token, entity_id, webhook_secret, api_host

    if cfg.hyperpay_secret_arn:
        loaded = load_hyperpay_from_secret(cfg.hyperpay_secret_arn)
        if loaded:
            return (
                loaded.access_token,
                loaded.entity_id,
                loaded.webhook_secret or webhook_secret,
                loaded.api_host or api_host,
            )

    return None


def get_payment_provider(cfg: BillingEdgeConfig) -> Optional[PaymentProviderPort]:
    """Select mock HyperPay, live HyperPay, or None (billing_unconfigured)."""
    if cfg.wants_mock():
        return MockHyperPayAdapter()

    if cfg.is_prod():
        if not cfg.has_hyperpay_secret_arn() and not cfg.has_hyperpay_inline_keys():
            return None
    elif (cfg.payment_provider or "").lower() != "hyperpay":
        return None
    else:
        if not cfg.has_hyperpay_inline_keys() and not cfg.has_hyperpay_secret_arn():
            return None

    creds = resolve_hyperpay_credentials(cfg)
    if creds is None:
        return None
    access_token, entity_id, _webhook_secret, api_host = creds
    if not (cfg.billing_shopper_result_url or "").strip():
        return None
    return HyperPayAdapter(
        access_token=access_token,
        entity_id=entity_id,
        api_host=api_host or _DEFAULT_API_HOST,
        deployment_environment=cfg.deployment_environment,
        shopper_result_url=cfg.billing_shopper_result_url,
    )
