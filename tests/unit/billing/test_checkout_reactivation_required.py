"""W6-P2 — checkout returns 409 reactivation_required when catalog blocks."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockPayTabsAdapter

_DEV_PLAN_ID = "a0000000-0000-4000-8000-000000000011"


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "mock",
        "paytabs_use_mock": True,
        "paytabs_secret_arn": None,
        "paytabs_server_key": None,
        "paytabs_profile_id": None,
        "paytabs_api_domain": None,
        "fulfillment_queue_url": "https://sqs.example.com/q",
        "catalog_lambda_arn": "arn:aws:lambda:eu-west-1:1:function:catalog",
        "subscription_plan_id": _DEV_PLAN_ID,
        "billing_return_success_url": "https://student.example.com/billing/success",
        "billing_return_cancel_url": "https://student.example.com/billing/cancel",
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _checkout_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "authorizer": {"claims": {"sub": "student-sub-1"}},
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"planId": _DEV_PLAN_ID}),
    }
    evt.update(overrides)
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_checkout_reactivation_required_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: {"blockReason": "reactivation_required"},
    )

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 409
    body = _parse_body(resp)
    assert body["code"] == "reactivation_required"
    assert body["message"]


def test_checkout_reactivation_required_does_not_call_paytabs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_provider = MagicMock()
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: mock_provider)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: {"blockReason": "reactivation_required"},
    )

    billing_handler.lambda_handler(_checkout_event(), None)
    mock_provider.create_subscribe_session.assert_not_called()
