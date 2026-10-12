"""WS2 slim checkout-session — HyperPay POST must not repeat shopperResultUrl."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any, Dict
from unittest.mock import MagicMock, patch
from urllib.parse import unquote_plus

import pytest

from billing._imports import (
    BillingEdgeConfig,
    HyperPayAdapter,
    billing_edge_handler,
    hyperpay_adapter,
)

_COURSE_ID = "b0000000-0000-4000-8000-000000000001"
_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_USER_SUB = "student-sub-checkout-1"
_USER_EMAIL = "shopper@example.com"
_CATALOG_ARN = "arn:aws:lambda:eu-west-1:123456789012:function:catalog"


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "hyperpay",
        "hyperpay_secret_arn": None,
        "hyperpay_access_token": "test-access-token",
        "hyperpay_entity_id": "test-entity-id",
        "hyperpay_webhook_secret": None,
        "fulfillment_queue_url": None,
        "catalog_lambda_arn": _CATALOG_ARN,
        "billing_shopper_result_url": "https://student.example.com/billing/result",
        "allowed_origins": ("https://student.example.com",),
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _checkout_session_event(**overrides: Any) -> Dict[str, Any]:
    body = {
        "productType": "course",
        "courseId": _COURSE_ID,
        "billing": {
            "givenName": "Ada",
            "surname": "Lovelace",
            "street": "1 Analytical Engine Rd",
            "city": "Amman",
            "state": "AM",
            "postcode": "11118",
            "country": "JO",
        },
    }
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "requestId": "req-checkout-session-1",
            "authorizer": {
                "claims": {"sub": _USER_SUB, "email": _USER_EMAIL},
            },
        },
        "headers": {
            "content-type": "application/json",
            "Origin": "https://student.example.com",
        },
        "body": json.dumps(body),
    }
    evt.update(overrides)
    return evt


def test_checkout_session_hyperpay_post_body_excludes_shopper_result_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OPPWA checkout creation must not set shopperResultUrl (widget sets it on Pay)."""
    captured_bodies: list[bytes] = []

    def fake_urlopen(req: Any, timeout: float = 30) -> MagicMock:
        _ = timeout
        if req.data:
            captured_bodies.append(req.data)
        response = MagicMock()
        response.read.return_value = json.dumps(
            {"id": "HP-CHECKOUT-ABC", "integrity": "sha384-mock"}
        ).encode("utf-8")
        response.__enter__ = lambda s: response
        response.__exit__ = MagicMock(return_value=False)
        return response

    catalog_calls: list[Dict[str, Any]] = []

    def fake_catalog_invoke(**kwargs: Any) -> Dict[str, Any]:
        catalog_calls.append(kwargs)
        return {
            "blockReason": None,
            "product": {
                "amount_minor": 50000,
                "currency": "JOD",
                "course_id": _COURSE_ID,
                "purchase_id": _PURCHASE_ID,
            },
        }

    provider = HyperPayAdapter(
        access_token="test-access-token",
        entity_id="test-entity-id",
        api_host="eu-test.oppwa.com",
        deployment_environment="dev",
        shopper_result_url="https://student.example.com/billing/result",
    )

    monkeypatch.setattr(billing_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_edge_handler, "_get_payment_provider", lambda _cfg: provider)
    monkeypatch.setattr(billing_edge_handler, "_invoke_billing_checkout", fake_catalog_invoke)

    with patch.object(hyperpay_adapter, "urlopen", side_effect=fake_urlopen):
        resp = billing_edge_handler.lambda_handler(_checkout_session_event(), None)

    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["checkoutId"] == "HP-CHECKOUT-ABC"
    assert body["purchaseId"] == _PURCHASE_ID
    assert catalog_calls[0]["user_sub"] == _USER_SUB
    assert catalog_calls[0]["product_type"] == "course"
    assert catalog_calls[0]["course_id"] == _COURSE_ID

    assert len(captured_bodies) == 1
    encoded = captured_bodies[0].decode("utf-8")
    assert "shopperResultUrl" not in encoded
    assert "shopperresulturl" not in encoded.lower()
    # Sanity: required OPPWA fields are present.
    assert "entityId=" in encoded
    assert unquote_plus(encoded).find("merchantTransactionId=") >= 0


def test_checkout_session_ignores_client_amount_minor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Server price from catalog precheck; browser amountMinor must not affect OPPWA create."""
    captured_bodies: list[bytes] = []

    def fake_urlopen(req: Any, timeout: float = 30) -> MagicMock:
        _ = timeout
        if req.data:
            captured_bodies.append(req.data)
        response = MagicMock()
        response.read.return_value = json.dumps(
            {"id": "HP-CHECKOUT-ABC", "integrity": "sha384-mock"}
        ).encode("utf-8")
        response.__enter__ = lambda s: response
        response.__exit__ = MagicMock(return_value=False)
        return response

    def fake_catalog_invoke(**kwargs: Any) -> Dict[str, Any]:
        return {
            "blockReason": None,
            "product": {
                "amount_minor": 50000,
                "currency": "JOD",
                "course_id": _COURSE_ID,
                "purchase_id": _PURCHASE_ID,
            },
        }

    provider = HyperPayAdapter(
        access_token="test-access-token",
        entity_id="test-entity-id",
        api_host="eu-test.oppwa.com",
        deployment_environment="dev",
        shopper_result_url="https://student.example.com/billing/result",
    )

    monkeypatch.setattr(billing_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_edge_handler, "_get_payment_provider", lambda _cfg: provider)
    monkeypatch.setattr(billing_edge_handler, "_invoke_billing_checkout", fake_catalog_invoke)

    evt = _checkout_session_event()
    body = json.loads(evt["body"])
    body["amountMinor"] = 999_000
    evt["body"] = json.dumps(body)

    with patch.object(hyperpay_adapter, "urlopen", side_effect=fake_urlopen):
        resp = billing_edge_handler.lambda_handler(evt, None)

    assert resp["statusCode"] == 200
    api_body = json.loads(resp["body"])
    assert api_body["amountMinor"] == 50000
    encoded = unquote_plus(captured_bodies[0].decode("utf-8"))
    assert "amount=50.00" in encoded or "amount=50" in encoded
    assert "999" not in encoded
