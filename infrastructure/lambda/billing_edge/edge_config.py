"""Billing edge environment configuration and provider factory."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from paytabs_secrets import load_paytabs_from_secret
from providers.mock_adapter import MockPayTabsAdapter
from providers.paytabs_adapter import PayTabsAdapter
from providers.port import PaymentProviderPort

_DEFAULT_API_DOMAIN = "secure-jordan.paytabs.com"


def _env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped or None


def _env_bool(name: str) -> bool:
    raw = _env(name)
    if raw is None:
        return False
    return raw.lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class BillingEdgeConfig:
    deployment_environment: str
    payment_provider: str | None
    paytabs_use_mock: bool
    paytabs_secret_arn: str | None
    paytabs_server_key: str | None
    paytabs_profile_id: str | None
    paytabs_api_domain: str | None
    fulfillment_queue_url: str | None
    catalog_lambda_arn: str | None
    subscription_plan_id: str | None
    billing_return_success_url: str | None
    billing_return_cancel_url: str | None

    def is_prod(self) -> bool:
        return self.deployment_environment.lower() == "prod"

    def wants_mock(self) -> bool:
        if self.is_prod():
            return self.paytabs_use_mock
        if (self.payment_provider or "").lower() == "mock":
            return True
        return self.paytabs_use_mock

    def has_paytabs_inline_keys(self) -> bool:
        return bool(self.paytabs_server_key and self.paytabs_profile_id)

    def has_paytabs_secret_arn(self) -> bool:
        return bool(self.paytabs_secret_arn)

    def is_configured(self) -> bool:
        return get_payment_provider(self) is not None


def load_billing_edge_config() -> BillingEdgeConfig:
    deployment = (_env("DEPLOYMENT_ENVIRONMENT") or "dev").lower()
    return BillingEdgeConfig(
        deployment_environment=deployment,
        payment_provider=_env("PAYMENT_PROVIDER"),
        paytabs_use_mock=_env_bool("PAYTABS_USE_MOCK"),
        paytabs_secret_arn=_env("PAYTABS_SECRET_ARN"),
        paytabs_server_key=_env("PAYTABS_SERVER_KEY"),
        paytabs_profile_id=_env("PAYTABS_PROFILE_ID"),
        paytabs_api_domain=_env("PAYTABS_API_DOMAIN") or _DEFAULT_API_DOMAIN,
        fulfillment_queue_url=_env("FULFILLMENT_QUEUE_URL"),
        catalog_lambda_arn=_env("CATALOG_LAMBDA_ARN"),
        subscription_plan_id=_env("SUBSCRIPTION_PLAN_ID"),
        billing_return_success_url=_env("BILLING_RETURN_SUCCESS_URL"),
        billing_return_cancel_url=_env("BILLING_RETURN_CANCEL_URL"),
    )


def resolve_paytabs_credentials(
    cfg: BillingEdgeConfig,
) -> tuple[str, str, str] | None:
    """Inline env first, then Secrets Manager when PAYTABS_SECRET_ARN is set."""
    server_key = cfg.paytabs_server_key or ""
    profile_id = cfg.paytabs_profile_id or ""
    api_domain = cfg.paytabs_api_domain or _DEFAULT_API_DOMAIN

    if server_key and profile_id:
        return server_key, profile_id, api_domain

    if cfg.paytabs_secret_arn:
        loaded = load_paytabs_from_secret(cfg.paytabs_secret_arn)
        if loaded:
            return (
                loaded.server_key,
                loaded.profile_id,
                loaded.api_domain or api_domain,
            )

    return None


def get_payment_provider(cfg: BillingEdgeConfig) -> Optional[PaymentProviderPort]:
    """Select mock, PayTabs, or None (billing_unconfigured)."""
    if cfg.wants_mock():
        return MockPayTabsAdapter(allow_mock_signature=True)

    if cfg.is_prod():
        if not cfg.has_paytabs_secret_arn() and not cfg.has_paytabs_inline_keys():
            return None
        creds = resolve_paytabs_credentials(cfg)
        if creds is None:
            return None
        server_key, profile_id, api_domain = creds
        return PayTabsAdapter(
            server_key=server_key,
            profile_id=profile_id,
            api_domain=api_domain,
            deployment_environment=cfg.deployment_environment,
            return_success_url=cfg.billing_return_success_url,
            return_cancel_url=cfg.billing_return_cancel_url,
        )

    if (cfg.payment_provider or "").lower() == "paytabs":
        creds = resolve_paytabs_credentials(cfg)
        if creds is None:
            return None
        server_key, profile_id, api_domain = creds
        return PayTabsAdapter(
            server_key=server_key,
            profile_id=profile_id,
            api_domain=api_domain,
            deployment_environment=cfg.deployment_environment,
            return_success_url=cfg.billing_return_success_url,
            return_cancel_url=cfg.billing_return_cancel_url,
        )

    return None
