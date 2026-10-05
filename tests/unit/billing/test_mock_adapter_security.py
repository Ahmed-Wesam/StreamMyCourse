"""MockHyperPayAdapter webhook decrypt (uses real AES-GCM via HyperPayAdapter)."""

from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from providers.mock_adapter import MockHyperPayAdapter

_KEY_HEX = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def _encrypt(payload: dict) -> tuple[bytes, str, str]:
    key = bytes.fromhex(_KEY_HEX)
    iv = bytes.fromhex("000000000000000000000000")
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]
    return ciphertext.hex().encode("ascii"), iv.hex(), tag.hex()


def test_mock_decrypt_webhook_round_trip() -> None:
    notification = {"type": "PAYMENT", "payload": {"id": "p1"}}
    body_hex, iv_hex, tag_hex = _encrypt(notification)
    decrypted = MockHyperPayAdapter.decrypt_webhook(
        ciphertext_hex=body_hex,
        iv_hex=iv_hex,
        auth_tag_hex=tag_hex,
        webhook_secret_hex=_KEY_HEX,
    )
    assert json.loads(decrypted.decode("utf-8")) == notification


def test_mock_decrypt_rejects_tampered_tag() -> None:
    body_hex, iv_hex, tag_hex = _encrypt({"type": "PAYMENT"})
    bad_tag = ("0" * 32) if tag_hex != ("0" * 32) else ("1" * 32)
    with pytest.raises(ValueError):
        MockHyperPayAdapter.decrypt_webhook(
            ciphertext_hex=body_hex,
            iv_hex=iv_hex,
            auth_tag_hex=bad_tag,
            webhook_secret_hex=_KEY_HEX,
        )
