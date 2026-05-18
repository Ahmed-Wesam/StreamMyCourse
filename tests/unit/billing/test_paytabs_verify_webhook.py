"""P2 — PayTabsAdapter.verify_webhook (HMAC-SHA256, stdlib only)."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from providers.paytabs_adapter import PayTabsAdapter


# Vectors aligned with PayTabs IPN docs: HMAC-SHA256(raw body, Server Key).
_SERVER_KEY = "SGJNZ96JLG-JDMKHGRWT9-RWRK2KJNRJ"
_RAW_BODY = b'{"cart_id":"cart_11111","tran_ref":"TST2215201242166"}'


def _expected_signature(body: bytes, server_key: str) -> str:
    return hmac.new(server_key.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_verify_webhook_accepts_valid_hmac() -> None:
    sig = _expected_signature(_RAW_BODY, _SERVER_KEY)
    assert PayTabsAdapter.verify_webhook(_RAW_BODY, sig, _SERVER_KEY) is True


def test_verify_webhook_rejects_wrong_signature() -> None:
    assert PayTabsAdapter.verify_webhook(_RAW_BODY, "deadbeef" * 8, _SERVER_KEY) is False


def test_verify_webhook_rejects_tampered_body() -> None:
    sig = _expected_signature(_RAW_BODY, _SERVER_KEY)
    tampered = _RAW_BODY + b"x"
    assert PayTabsAdapter.verify_webhook(tampered, sig, _SERVER_KEY) is False


def test_verify_webhook_rejects_empty_server_key() -> None:
    sig = _expected_signature(_RAW_BODY, _SERVER_KEY)
    assert PayTabsAdapter.verify_webhook(_RAW_BODY, sig, "") is False


def test_verify_webhook_rejects_empty_signature_header() -> None:
    assert PayTabsAdapter.verify_webhook(_RAW_BODY, "", _SERVER_KEY) is False


@pytest.mark.parametrize(
    "signature_header",
    [
        _expected_signature(_RAW_BODY, _SERVER_KEY).upper(),
    ],
)
def test_verify_webhook_is_case_insensitive_for_hex(signature_header: str) -> None:
    assert PayTabsAdapter.verify_webhook(_RAW_BODY, signature_header, _SERVER_KEY) is True
