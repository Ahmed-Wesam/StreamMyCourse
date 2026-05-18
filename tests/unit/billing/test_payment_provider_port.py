"""P1 — PaymentProviderPort + MockPayTabsAdapter."""

from __future__ import annotations

import pytest

from providers.mock_adapter import MockPayTabsAdapter
from providers.port import PaymentProviderPort, SubscribeSessionResult


def test_mock_adapter_satisfies_port_protocol() -> None:
    adapter: PaymentProviderPort = MockPayTabsAdapter()
    assert isinstance(adapter, PaymentProviderPort)


def test_mock_create_subscribe_session_returns_redirect_url() -> None:
    adapter = MockPayTabsAdapter()
    result = adapter.create_subscribe_session(
        user_sub="user-abc",
        plan_id="plan-monthly",
        return_url="https://student.example.com/billing/return",
    )
    assert isinstance(result, SubscribeSessionResult)
    assert result.redirect_url.startswith("https://")
    assert "mock" in result.redirect_url.lower() or "example" in result.redirect_url


def test_mock_parse_webhook_returns_empty_list() -> None:
    adapter = MockPayTabsAdapter()
    assert adapter.parse_webhook(b"{}") == []


def test_mock_cancel_agreement_raises_not_implemented() -> None:
    adapter = MockPayTabsAdapter()
    with pytest.raises(NotImplementedError):
        adapter.cancel_agreement("agreement-1")
