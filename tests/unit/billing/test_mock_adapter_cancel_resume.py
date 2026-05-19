"""W8-P4 — MockPayTabsAdapter.cancel_agreement is a no-op (no outbound HTTP)."""

from __future__ import annotations

from providers.mock_adapter import MockPayTabsAdapter
from providers.port import PaymentProviderPort


def test_mock_cancel_agreement_no_op() -> None:
    adapter = MockPayTabsAdapter()
    assert isinstance(adapter, PaymentProviderPort)
    adapter.cancel_agreement("agreement-1")
