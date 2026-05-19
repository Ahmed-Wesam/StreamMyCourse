"""W8-P4 — PaymentProviderPort.cancel_agreement (mock adapter satisfies port)."""

from __future__ import annotations

from providers.mock_adapter import MockPayTabsAdapter
from providers.port import PaymentProviderPort


def test_payment_provider_port_declares_cancel_agreement() -> None:
    assert hasattr(PaymentProviderPort, "cancel_agreement")


def test_mock_adapter_satisfies_port_with_cancel() -> None:
    adapter: PaymentProviderPort = MockPayTabsAdapter()
    assert isinstance(adapter, PaymentProviderPort)
    adapter.cancel_agreement("agreement-1")
