"""P3 — billing_edge config + get_payment_provider factory."""

from __future__ import annotations

import pytest

from edge_config import BillingEdgeConfig, get_payment_provider, load_billing_edge_config
from providers.mock_adapter import MockPayTabsAdapter
from providers.paytabs_adapter import PayTabsAdapter


def _clear_paytabs_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "DEPLOYMENT_ENVIRONMENT",
        "PAYMENT_PROVIDER",
        "PAYTABS_USE_MOCK",
        "PAYTABS_SECRET_ARN",
        "PAYTABS_SERVER_KEY",
        "PAYTABS_PROFILE_ID",
        "PAYTABS_API_DOMAIN",
    ):
        monkeypatch.delenv(key, raising=False)


def test_prod_paytabs_use_mock_selects_mock_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("PAYTABS_USE_MOCK", "true")
    provider = get_payment_provider(load_billing_edge_config())
    assert isinstance(provider, MockPayTabsAdapter)


def test_prod_payment_provider_mock_without_paytabs_use_mock_is_not_mock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    provider = get_payment_provider(load_billing_edge_config())
    assert provider is None or isinstance(provider, PayTabsAdapter)
    assert not isinstance(provider, MockPayTabsAdapter)


def test_prod_without_secret_arn_is_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("PAYMENT_PROVIDER", "paytabs")
    cfg = load_billing_edge_config()
    assert cfg.is_configured() is False
    assert get_payment_provider(cfg) is None


def test_prod_with_secret_arn_only_loads_from_sm(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("PAYTABS_SECRET_ARN", "arn:aws:secretsmanager:eu-west-1:1:secret:test")

    from paytabs_secrets import PaytabsCredentials, clear_paytabs_secret_cache

    clear_paytabs_secret_cache()

    def _fake_load(secret_id: str) -> PaytabsCredentials:
        assert secret_id.startswith("arn:")
        return PaytabsCredentials(
            server_key="sm-server-key",
            profile_id="sm-profile",
            api_domain="secure-jordan.paytabs.com",
        )

    import edge_config as billing_edge_config

    monkeypatch.setattr(billing_edge_config, "load_paytabs_from_secret", _fake_load)
    cfg = load_billing_edge_config()
    provider = get_payment_provider(cfg)
    assert isinstance(provider, PayTabsAdapter)
    assert provider.server_key == "sm-server-key"


def test_prod_with_secret_arn_and_inline_keys_uses_paytabs(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("PAYTABS_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:1:secret:x")
    monkeypatch.setenv("PAYTABS_SERVER_KEY", "prod-server-key")
    monkeypatch.setenv("PAYTABS_PROFILE_ID", "profile-1")
    cfg = load_billing_edge_config()
    provider = get_payment_provider(cfg)
    assert isinstance(provider, PayTabsAdapter)


def test_dev_mock_only_when_payment_provider_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    monkeypatch.setenv("PAYMENT_PROVIDER", "mock")
    provider = get_payment_provider(load_billing_edge_config())
    assert isinstance(provider, MockPayTabsAdapter)


def test_dev_mock_only_when_paytabs_use_mock_true(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    monkeypatch.setenv("PAYTABS_USE_MOCK", "true")
    provider = get_payment_provider(load_billing_edge_config())
    assert isinstance(provider, MockPayTabsAdapter)


def test_dev_without_explicit_mock_flag_is_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    cfg = load_billing_edge_config()
    assert get_payment_provider(cfg) is None


def test_dev_paytabs_when_keys_present(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_paytabs_env(monkeypatch)
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "dev")
    monkeypatch.setenv("PAYMENT_PROVIDER", "paytabs")
    monkeypatch.setenv("PAYTABS_SERVER_KEY", "dev-key")
    monkeypatch.setenv("PAYTABS_PROFILE_ID", "dev-profile")
    provider = get_payment_provider(load_billing_edge_config())
    assert isinstance(provider, PayTabsAdapter)


def test_billing_edge_config_is_frozen_dataclass() -> None:
    cfg = BillingEdgeConfig(
        deployment_environment="dev",
        payment_provider=None,
        paytabs_use_mock=False,
        paytabs_secret_arn=None,
        paytabs_server_key=None,
        paytabs_profile_id=None,
        paytabs_api_domain=None,
        fulfillment_queue_url=None,
    )
    with pytest.raises(AttributeError):
        cfg.deployment_environment = "prod"  # type: ignore[misc]
