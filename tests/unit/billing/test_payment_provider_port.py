"""P1 — PaymentProviderPort + MockPayTabsAdapter."""

from __future__ import annotations

from providers.mock_adapter import MockPayTabsAdapter
from providers.port import CheckoutProduct, PaymentProviderPort, SubscribeSessionResult


def test_mock_adapter_satisfies_port_protocol() -> None:
    adapter: PaymentProviderPort = MockPayTabsAdapter()
    assert isinstance(adapter, PaymentProviderPort)


def test_mock_create_sale_session_returns_redirect_url() -> None:
    adapter = MockPayTabsAdapter()
    result = adapter.create_sale_session(
        user_sub="user-abc",
        purchase_id="c0000000-0000-4000-8000-000000000001",
        product_type="course",
        course_id="b0000000-0000-4000-8000-000000000001",
        product=CheckoutProduct(amount_minor=9900, currency="USD", description="course"),
    )
    assert isinstance(result, SubscribeSessionResult)
    assert result.redirect_url.startswith("https://")
    assert "mock" in result.redirect_url.lower() or "example" in result.redirect_url


def test_mock_parse_webhook_returns_empty_list() -> None:
    adapter = MockPayTabsAdapter()
    assert adapter.parse_webhook(b"{}", deployment_environment="dev") == []
