"""W7-P4 — PaymentProviderPort.resume_agreement."""

from __future__ import annotations

from providers.mock_adapter import MockPayTabsAdapter
from providers.port import PaymentProviderPort


def test_payment_provider_port_declares_resume_agreement() -> None:
    assert hasattr(PaymentProviderPort, "resume_agreement")


def test_mock_adapter_satisfies_port_with_resume() -> None:
    adapter: PaymentProviderPort = MockPayTabsAdapter()
    assert isinstance(adapter, PaymentProviderPort)
    adapter.resume_agreement("agreement-1")
