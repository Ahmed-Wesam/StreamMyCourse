"""P1 — PaymentProviderPort + MockHyperPayAdapter."""

from __future__ import annotations

from domain.checkout_billing import CheckoutBillingContact
from providers.mock_adapter import MockHyperPayAdapter
from providers.port import CheckoutProduct, HyperPayCheckoutResult, PaymentProviderPort

_BILLING = CheckoutBillingContact(
    given_name="A",
    surname="B",
    street="1 St",
    city="Amman",
    state="Amman",
    postcode="11118",
    country="JO",
)


def test_mock_adapter_satisfies_port_protocol() -> None:
    adapter: PaymentProviderPort = MockHyperPayAdapter()
    assert isinstance(adapter, PaymentProviderPort)


def test_mock_create_checkout_returns_widget_fields() -> None:
    adapter = MockHyperPayAdapter()
    result = adapter.create_checkout(
        user_sub="user-abc",
        purchase_id="c0000000-0000-4000-8000-000000000001",
        product_type="course",
        course_id="b0000000-0000-4000-8000-000000000001",
        product=CheckoutProduct(amount_minor=50_000, currency="JOD", description="course"),
        customer_email="student@example.com",
        billing=_BILLING,
    )
    assert isinstance(result, HyperPayCheckoutResult)
    assert result.checkout_id
    assert "paymentWidgets.js" in result.widget_url


def test_mock_fetch_checkout_result_pending() -> None:
    adapter = MockHyperPayAdapter()
    payload = adapter.fetch_checkout_result("MOCK-HP-CHECKOUT")
    assert payload["result"]["code"].startswith("000.200")
