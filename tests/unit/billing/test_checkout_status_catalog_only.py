"""WS2 slim checkout-status — catalog purchaseId only, no HyperPay GET /payment poll."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import (
    BILLING_EDGE_DIR,
    BillingEdgeConfig,
    billing_edge_handler,
)

_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_USER_SUB = "student-sub-status-1"
_CATALOG_ARN = "arn:aws:lambda:eu-west-1:123456789012:function:catalog"


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "mock",
        "hyperpay_secret_arn": None,
        "hyperpay_access_token": None,
        "hyperpay_entity_id": None,
        "hyperpay_webhook_secret": None,
        "fulfillment_queue_url": None,
        "catalog_lambda_arn": _CATALOG_ARN,
        "billing_shopper_result_url": "https://student.example.com/billing/result",
        "allowed_origins": ("https://student.example.com",),
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _checkout_status_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-status",
        "requestContext": {
            "resourcePath": "/billing/checkout-status",
            "requestId": "req-checkout-status-1",
            "authorizer": {
                "claims": {"sub": _USER_SUB, "email": "shopper@example.com"},
            },
        },
        "headers": {
            "content-type": "application/json",
            "Origin": "https://student.example.com",
        },
        "body": json.dumps({"purchaseId": _PURCHASE_ID}),
    }
    evt.update(overrides)
    return evt


def test_checkout_status_handler_does_not_use_hyperpay_poll_helpers() -> None:
    """Slim edge must not call fetch_checkout_result or parse_checkout_payment_poll."""
    handler_path = BILLING_EDGE_DIR / "handler.py"
    assert handler_path.is_file(), "billing_edge handler.py missing"
    source = handler_path.read_text(encoding="utf-8")
    assert "fetch_checkout_result" not in source
    assert "parse_checkout_payment_poll" not in source


def test_checkout_status_invokes_catalog_with_purchase_id_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    status_calls: list[Dict[str, Any]] = []
    fetch_calls: list[str] = []

    class NoPollProvider:
        def fetch_checkout_result(self, checkout_id: str) -> Dict[str, Any]:
            fetch_calls.append(checkout_id)
            raise AssertionError("checkout-status must not poll HyperPay")

    monkeypatch.setattr(billing_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_edge_handler,
        "_get_payment_provider",
        lambda _cfg: NoPollProvider(),
    )
    monkeypatch.setattr(
        billing_edge_handler,
        "_invoke_billing_checkout_status",
        lambda **kw: status_calls.append(kw) or {"status": "paid"},
    )

    resp = billing_edge_handler.lambda_handler(_checkout_status_event(), None)

    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"status": "paid"}
    assert fetch_calls == []
    assert len(status_calls) == 1
    call = status_calls[0]
    assert call["user_sub"] == _USER_SUB
    assert call["purchase_id"] == _PURCHASE_ID
    assert call["catalog_lambda_arn"] == _CATALOG_ARN
    assert call.get("amount_minor") is None
    assert call.get("currency") is None


def test_checkout_status_requires_purchase_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_edge_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_edge_handler,
        "_get_payment_provider",
        lambda _cfg: MagicMock(),
    )

    resp = billing_edge_handler.lambda_handler(
        _checkout_status_event(body=json.dumps({"checkoutId": "HP-OLD-FLOW"})),
        None,
    )

    assert resp["statusCode"] == 400
    payload = json.loads(resp["body"])
    assert payload["code"] == "invalid_request"
    assert "purchaseid" in payload["message"].lower()
