"""HyperPay webhook decrypt + parse (AES-GCM, domain events)."""

from __future__ import annotations

import json
from typing import Any

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from domain.metadata import InvalidCartMetadataError
from providers.hyperpay_adapter import HyperPayAdapter, parse_hyperpay_webhook

_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"
_USER_SUB = "student-sub-1"
_CART_V2_COURSE = f"v2|dev|{_USER_SUB}|course|{_COURSE_ID}|{_PURCHASE_ID}"
_DIGEST = "d" * 64

_WEBHOOK_KEY_HEX = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def _encrypt_notification(
    payload: dict[str, Any],
    *,
    key_hex: str = _WEBHOOK_KEY_HEX,
    iv_hex: str | None = None,
) -> tuple[bytes, str, str]:
    key = bytes.fromhex(key_hex)
    iv = bytes.fromhex(iv_hex or "000000000000000000000000")
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]
    return ciphertext.hex().encode("ascii"), iv.hex(), tag.hex()


def _payment_notification(
    *,
    payment_type: str = "DB",
    result_code: str = "000.000.000",
    merchant_transaction_id: str = _CART_V2_COURSE,
    payment_id: str = "8a8294174e735d0c014e78cf26461790",
) -> dict[str, Any]:
    return {
        "type": "PAYMENT",
        "action": "CREATED",
        "payload": {
            "id": payment_id,
            "paymentType": payment_type,
            "amount": "50.00",
            "currency": "JOD",
            "merchantTransactionId": merchant_transaction_id,
            "result": {"code": result_code, "description": "Transaction succeeded"},
        },
    }


def _parse(payload: dict[str, Any], *, deployment: str = "dev") -> list:
    return parse_hyperpay_webhook(
        json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        deployment_environment=deployment,
        payload_digest=_DIGEST,
    )


def test_decrypt_webhook_round_trip() -> None:
    adapter = HyperPayAdapter(
        access_token="t",
        entity_id="e",
        api_host="eu-test.oppwa.com",
        deployment_environment="dev",
    )
    notification = _payment_notification()
    body_hex, iv_hex, tag_hex = _encrypt_notification(notification)
    decrypted = adapter.decrypt_webhook(
        ciphertext_hex=body_hex,
        iv_hex=iv_hex,
        auth_tag_hex=tag_hex,
        webhook_secret_hex=_WEBHOOK_KEY_HEX,
    )
    assert json.loads(decrypted.decode("utf-8")) == notification


def test_decrypt_webhook_rejects_tampered_auth_tag() -> None:
    adapter = HyperPayAdapter(
        access_token="t",
        entity_id="e",
        api_host="eu-test.oppwa.com",
        deployment_environment="dev",
    )
    body_hex, iv_hex, tag_hex = _encrypt_notification(_payment_notification())
    bad_tag = ("0" * 32) if tag_hex != ("0" * 32) else ("1" * 32)
    with pytest.raises(ValueError):
        adapter.decrypt_webhook(
            ciphertext_hex=body_hex,
            iv_hex=iv_hex,
            auth_tag_hex=bad_tag,
            webhook_secret_hex=_WEBHOOK_KEY_HEX,
        )


def test_db_success_maps_to_purchase_paid() -> None:
    events = _parse(_payment_notification(result_code="000.000.000"))
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "purchase.paid"
    assert event.provider == "hyperpay"
    assert event.purchase_id == _PURCHASE_ID
    assert event.amount_minor == 50_000
    assert event.currency == "JOD"
    assert event.provider_event_id.startswith("hyperpay:")


def test_db_decline_maps_to_purchase_failed() -> None:
    events = _parse(_payment_notification(result_code="800.100.153"))
    assert len(events) == 1
    assert events[0].event_type == "purchase.failed"
    assert events[0].provider == "hyperpay"


def test_pending_000_200_does_not_emit_failed_event() -> None:
    events = _parse(_payment_notification(result_code="000.200.000"))
    assert events == []


def test_rf_maps_to_purchase_revoked() -> None:
    note = _payment_notification(
        payment_type="RF",
        result_code="000.000.000",
        payment_id="REFUND-PAY-1",
    )
    note["payload"]["referencedId"] = "8a8294174e735d0c014e78cf26461790"
    events = _parse(note)
    assert len(events) == 1
    assert events[0].event_type == "purchase.revoked"
    assert events[0].provider_tran_ref == "8a8294174e735d0c014e78cf26461790"


def test_unknown_notification_type_is_ignored() -> None:
    events = _parse(
        {
            "type": "REGISTRATION",
            "action": "CREATED",
            "payload": {"id": "reg-1"},
        }
    )
    assert events == []


def test_db_without_merchant_transaction_id_raises() -> None:
    note = _payment_notification()
    del note["payload"]["merchantTransactionId"]
    with pytest.raises(InvalidCartMetadataError):
        _parse(note)


def test_hyperpay_adapter_parse_webhook_delegates() -> None:
    adapter = HyperPayAdapter(
        access_token="t",
        entity_id="e",
        api_host="eu-test.oppwa.com",
        deployment_environment="dev",
    )
    events = adapter.parse_webhook(
        json.dumps(_payment_notification(), separators=(",", ":")).encode("utf-8"),
        deployment_environment="dev",
        payload_digest=_DIGEST,
    )
    assert len(events) == 1
    assert events[0].event_type == "purchase.paid"
