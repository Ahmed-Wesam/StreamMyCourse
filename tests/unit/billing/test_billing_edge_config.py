"""P3 — billing_edge config + get_payment_provider factory (HyperPay)."""

from __future__ import annotations

import pytest

from edge_config import BillingEdgeConfig, get_payment_provider, load_billing_edge_config
from providers.mock_adapter import MockHyperPayAdapter
from providers.hyperpay_adapter import HyperPayAdapter


def _clear_hyperpay_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DEPLOYMENT_ENVIRONMENT",
        "PAYMENT_PROVIDER",
        "HYPERPAY_SECRET_ARN",
        "HYPERPAY_ACCESS_TOKEN",
        "HYPERPAY_ENTITY_ID",
        "HYPERPAY_WEBHOOK_SECRET",
        "BILLING_SHOPPER_RESULT_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_prod_payment_provider_mock_selects_mock_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hyperpay_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    provider = get_payment_provider(load_billing_edge_config())
    assert isinstance(provider, MockHyperPayAdapter)


def test_prod_without_secret_arn_is_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hyperpay_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("PAYMENT_PROVIDER", "hyperpay")
    cfg = load_billing_edge_config()
    assert cfg.is_configured() is False
    assert get_payment_provider(cfg) is None


def test_prod_with_secret_arn_only_loads_from_sm(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hyperpay_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("HYPERPAY_SECRET_ARN", "arn:aws:secretsmanager:eu-west-1:1:secret:test")
    monkeypatch.setenv("BILLING_SHOPPER_RESULT_URL", "https://student.example.com/billing/result")

    from hyperpay_secrets import HyperpayCredentials, clear_hyperpay_secret_cache

    clear_hyperpay_secret_cache()

    def _fake_load(secret_id: str) -> HyperpayCredentials:
        assert secret_id.startswith("arn:")
        return HyperpayCredentials(
            access_token="sm-token",
            entity_id="sm-entity",
            webhook_secret="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            api_host="eu-test.oppwa.com",
        )

    import edge_config as billing_edge_config

    monkeypatch.setattr(billing_edge_config, "load_hyperpay_from_secret", _fake_load)
    cfg = load_billing_edge_config()
    provider = get_payment_provider(cfg)
    assert isinstance(provider, HyperPayAdapter)


def test_dev_mock_only_when_payment_provider_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hyperpay_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    provider = get_payment_provider(load_billing_edge_config())
    assert isinstance(provider, MockHyperPayAdapter)


def test_dev_without_explicit_mock_flag_is_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hyperpay_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    cfg = load_billing_edge_config()
    assert get_payment_provider(cfg) is None


def test_dev_hyperpay_when_inline_keys_present(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_hyperpay_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    monkeypatch.setenv("PAYMENT_PROVIDER", "hyperpay")
    monkeypatch.setenv("HYPERPAY_ACCESS_TOKEN", "dev-token")
    monkeypatch.setenv("HYPERPAY_ENTITY_ID", "dev-entity")
    monkeypatch.setenv("BILLING_SHOPPER_RESULT_URL", "https://student.example.com/billing/result")
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "https://researchspectrum.org,https://teach.researchspectrum.org",
    )
    cfg = load_billing_edge_config()
    assert cfg.allowed_origins == (
        "https://researchspectrum.org",
        "https://teach.researchspectrum.org",
    )
    provider = get_payment_provider(cfg)
    assert isinstance(provider, HyperPayAdapter)


def test_billing_edge_config_is_frozen_dataclass() -> None:
    cfg = BillingEdgeConfig(
        deployment_environment="dev",
        payment_provider=None,
        hyperpay_secret_arn=None,
        hyperpay_access_token=None,
        hyperpay_entity_id=None,
        hyperpay_webhook_secret=None,
        fulfillment_queue_url=None,
        catalog_lambda_arn=None,
        billing_shopper_result_url=None,
        allowed_origins=(),
    )
    with pytest.raises(AttributeError):
        cfg.deployment_environment = "prod"  # type: ignore[misc]
