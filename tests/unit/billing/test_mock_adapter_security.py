"""MockPayTabsAdapter webhook verification."""

from __future__ import annotations

import hashlib
import hmac
import json

from providers.mock_adapter import MOCK_IPN_SALE_ACTIVATED, MockPayTabsAdapter
from providers.paytabs_adapter import PayTabsAdapter


def test_mock_rejects_test_signature_when_server_key_configured() -> None:
    raw = MockPayTabsAdapter.sample_ipn_bytes(MOCK_IPN_SALE_ACTIVATED)
    adapter = MockPayTabsAdapter(allow_mock_signature=True)
    assert adapter.verify_webhook(raw, "test", "server-key") is False


def test_mock_accepts_hmac_when_server_key_configured() -> None:
    server_key = "server-key"
    raw = MockPayTabsAdapter.sample_ipn_bytes(MOCK_IPN_SALE_ACTIVATED)
    sig = hmac.new(server_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    adapter = MockPayTabsAdapter(allow_mock_signature=True)
    assert adapter.verify_webhook(raw, sig, server_key) is True
    assert PayTabsAdapter.verify_webhook(raw, sig, server_key) is True


def test_mock_accepts_test_signature_without_server_key() -> None:
    raw = MockPayTabsAdapter.sample_ipn_bytes(MOCK_IPN_SALE_ACTIVATED)
    adapter = MockPayTabsAdapter(allow_mock_signature=True)
    assert adapter.verify_webhook(raw, "test", "") is True
