"""P4 / W3-P4 — billing_edge HTTP handler (HyperPay checkout + webhooks)."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from billing._imports import billing_handler
from domain.events import BillingDomainEvent
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockHyperPayAdapter
from providers.hyperpay_adapter import BillingUnconfiguredError
from queue_shim import EnqueueError

_QUEUE_URL = "https://sqs.eu-west-1.amazonaws.com/1/test-queue"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"
_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_USER_SUB = "student-sub-1"
_CART_V2 = f"v2|dev|{_USER_SUB}|course|{_COURSE_ID}|{_PURCHASE_ID}"
_WEBHOOK_KEY_HEX = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
_SHOPPER_RESULT_URL = "https://student.example.com/billing/result"
_CHECKOUT_BILLING = {
    "givenName": "Ada",
    "surname": "Student",
    "street": "1 King Hussein St",
    "city": "Amman",
    "state": "Amman",
    "postcode": "11118",
    "country": "JO",
}


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "mock",
        "hyperpay_secret_arn": None,
        "hyperpay_access_token": None,
        "hyperpay_entity_id": None,
        "hyperpay_webhook_secret": _WEBHOOK_KEY_HEX,
        "fulfillment_queue_url": _QUEUE_URL,
        "catalog_lambda_arn": "arn:aws:lambda:eu-west-1:1:function:catalog",
        "billing_shopper_result_url": _SHOPPER_RESULT_URL,
        "allowed_origins": ("https://researchspectrum.org",),
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _catalog_ok(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "blockReason": None,
        "product": {
            "amount_minor": 50_000,
            "currency": "JOD",
            "course_id": _COURSE_ID,
            "purchase_id": _PURCHASE_ID,
        },
    }
    payload.update(overrides)
    return payload


def _checkout_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "stage": "dev",
            "authorizer": {
                "claims": {"sub": _USER_SUB, "email": "student@example.com"},
            },
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "productType": "course",
                "courseId": _COURSE_ID,
                "billing": _CHECKOUT_BILLING,
            }
        ),
    }
    evt.update(overrides)
    return evt


def _checkout_status_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-status",
        "requestContext": {
            "resourcePath": "/billing/checkout-status",
            "stage": "dev",
            "authorizer": {"claims": {"sub": _USER_SUB}},
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"checkoutId": "MOCK-HP-CHECKOUT"}),
    }
    evt.update(overrides)
    return evt


def _encrypt_notification(payload: dict[str, Any]) -> tuple[bytes, str, str]:
    key = bytes.fromhex(_WEBHOOK_KEY_HEX)
    iv = bytes.fromhex("000000000000000000000000")
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]
    return ciphertext.hex().encode("ascii"), iv.hex(), tag.hex()


def _hyperpay_webhook_event(
    *,
    body_hex: bytes,
    iv_hex: str,
    tag_hex: str,
    request_id: str = "req-test-1",
) -> Dict[str, Any]:
    return {
        "httpMethod": "POST",
        "path": "/webhooks/payments/hyperpay",
        "requestContext": {
            "resourcePath": "/webhooks/payments/hyperpay",
            "stage": "dev",
            "requestId": request_id,
        },
        "headers": {
            "content-type": "application/json",
            "X-Initialization-Vector": iv_hex,
            "X-Authentication-Tag": tag_hex,
        },
        "body": body_hex.decode("ascii"),
        "isBase64Encoded": False,
    }


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def _patch_mock_checkout(monkeypatch: pytest.MonkeyPatch, **config_overrides: Any) -> None:
    cfg = _edge_config(**config_overrides)
    monkeypatch.setattr(billing_handler, "_load_config", lambda: cfg)
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockHyperPayAdapter(),
    )


def test_checkout_returns_503_billing_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: _edge_config(payment_provider=None),
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: None)

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


def test_checkout_status_options_succeeds_when_billing_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: _edge_config(payment_provider="hyperpay", billing_shopper_result_url=""),
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: None)

    evt = _checkout_status_event()
    evt["httpMethod"] = "OPTIONS"
    evt["headers"] = {"Origin": "https://researchspectrum.org"}
    resp = billing_handler.lambda_handler(evt, None)

    assert resp["statusCode"] == 204
    assert resp["headers"]["Access-Control-Allow-Origin"] == "https://researchspectrum.org"


def test_checkout_returns_401_without_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    evt = _checkout_event()
    evt["requestContext"] = {"resourcePath": "/billing/checkout-session"}

    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_checkout_empty_body_returns_invalid_request(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    resp = billing_handler.lambda_handler(_checkout_event(body=""), None)
    assert resp["statusCode"] == 400
    assert _parse_body(resp)["code"] == "invalid_request"


def test_checkout_not_implemented_invokes_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    rollback_calls: list[str] = []

    class NotImplementedProvider(MockHyperPayAdapter):
        def create_checkout(self, **kwargs: Any) -> Any:
            raise NotImplementedError()

    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: NotImplementedProvider(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: _catalog_ok(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout_rollback",
        lambda *, user_sub, product_type, course_id, catalog_lambda_arn: rollback_calls.append(
            user_sub
        ),
    )

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 501
    assert rollback_calls == [_USER_SUB]


def test_checkout_session_failure_invokes_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    rollback_calls: list[str] = []

    class FailingProvider(MockHyperPayAdapter):
        def create_checkout(self, **kwargs: Any) -> Any:
            raise BillingUnconfiguredError()

    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: FailingProvider(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: _catalog_ok(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout_rollback",
        lambda *, user_sub, product_type, course_id, catalog_lambda_arn: rollback_calls.append(
            user_sub
        ),
    )

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 503
    assert rollback_calls == [_USER_SUB]


def test_checkout_mock_returns_hyperpay_widget_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: _catalog_ok(),
    )

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 200
    body = _parse_body(resp)
    assert body["checkoutId"] == "MOCK-HP-CHECKOUT"
    assert body["integrity"] == "sha384-mock"
    assert "paymentWidgets.js" in body["widgetScriptUrl"]
    assert body["shopperResultUrl"] == _SHOPPER_RESULT_URL
    assert body["purchaseId"] == _PURCHASE_ID
    assert body["amountMinor"] == 50_000
    assert body["currency"] == "JOD"


def test_checkout_status_pending_does_not_enqueue(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    enqueue = MagicMock()
    monkeypatch.setattr(billing_handler, "_enqueue_domain_events", enqueue)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout_status",
        lambda **_kw: {"ok": True},
    )

    resp = billing_handler.lambda_handler(_checkout_status_event(), None)
    assert resp["statusCode"] == 200
    assert _parse_body(resp) == {"status": "pending"}
    enqueue.assert_not_called()


def test_checkout_status_requires_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    evt = _checkout_status_event()
    evt["requestContext"] = {"resourcePath": "/billing/checkout-status"}
    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 401


def test_paytabs_webhook_route_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    evt = {
        "httpMethod": "POST",
        "path": "/webhooks/payments/paytabs",
        "requestContext": {"resourcePath": "/webhooks/payments/paytabs"},
        "body": "{}",
    }
    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 404


def test_hyperpay_webhook_returns_503_when_webhook_secret_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_mock_checkout(monkeypatch, hyperpay_webhook_secret=None)
    body_hex, iv_hex, tag_hex = _encrypt_notification({"type": "PAYMENT", "payload": {}})
    resp = billing_handler.lambda_handler(
        _hyperpay_webhook_event(body_hex=body_hex, iv_hex=iv_hex, tag_hex=tag_hex),
        None,
    )
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


def test_hyperpay_webhook_bad_decrypt_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    body_hex, iv_hex, _tag_hex = _encrypt_notification({"type": "PAYMENT", "payload": {}})
    bad_tag = "0" * 32
    resp = billing_handler.lambda_handler(
        _hyperpay_webhook_event(body_hex=body_hex, iv_hex=iv_hex, tag_hex=bad_tag),
        None,
    )
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "invalid_webhook"


def test_hyperpay_webhook_valid_decrypt_enqueues_purchase_paid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_mock_checkout(monkeypatch)
    enqueue = MagicMock()
    monkeypatch.setattr(billing_handler, "_enqueue_domain_events", enqueue)
    notification = {
        "type": "PAYMENT",
        "action": "CREATED",
        "payload": {
            "id": "pay-1",
            "paymentType": "DB",
            "amount": "50.00",
            "currency": "JOD",
            "merchantTransactionId": _CART_V2,
            "result": {"code": "000.000.000"},
        },
    }
    body_hex, iv_hex, tag_hex = _encrypt_notification(notification)
    resp = billing_handler.lambda_handler(
        _hyperpay_webhook_event(body_hex=body_hex, iv_hex=iv_hex, tag_hex=tag_hex),
        None,
    )
    assert resp["statusCode"] == 200
    enqueue.assert_called_once()
    events: List[BillingDomainEvent] = enqueue.call_args[0][0]
    assert len(events) == 1
    assert events[0].event_type == "purchase.paid"


def test_webhook_enqueue_failure_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_checkout(monkeypatch)
    enqueue = MagicMock(side_effect=EnqueueError("SQS down"))
    monkeypatch.setattr(billing_handler, "_enqueue_domain_events", enqueue)
    notification = {
        "type": "PAYMENT",
        "payload": {
            "id": "pay-2",
            "paymentType": "DB",
            "amount": "50.00",
            "currency": "JOD",
            "merchantTransactionId": _CART_V2,
            "result": {"code": "000.000.000"},
        },
    }
    body_hex, iv_hex, tag_hex = _encrypt_notification(notification)
    resp = billing_handler.lambda_handler(
        _hyperpay_webhook_event(body_hex=body_hex, iv_hex=iv_hex, tag_hex=tag_hex),
        None,
    )
    assert resp["statusCode"] == 500
    assert _parse_body(resp)["code"] == "enqueue_failed"
