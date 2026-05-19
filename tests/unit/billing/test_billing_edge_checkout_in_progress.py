"""W6 — checkout returns 409 checkout_in_progress when catalog blocks fresh incomplete."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockPayTabsAdapter

_CATALOG_ARN = "arn:aws:lambda:eu-west-1:1:function:catalog"
_PLAN_ID = "a0000000-0000-4000-8000-000000000011"


def _edge_config() -> BillingEdgeConfig:
    return BillingEdgeConfig(
        deployment_environment="dev",
        payment_provider="mock",
        paytabs_use_mock=True,
        paytabs_secret_arn=None,
        paytabs_server_key=None,
        paytabs_profile_id=None,
        paytabs_api_domain=None,
        fulfillment_queue_url="https://sqs.eu-west-1.amazonaws.com/1/q",
        catalog_lambda_arn=_CATALOG_ARN,
        subscription_plan_id=_PLAN_ID,
        billing_return_success_url="https://student.example.com/billing/success",
        billing_return_cancel_url="https://student.example.com/billing/cancel",
    )


def _checkout_event() -> Dict[str, Any]:
    return {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "authorizer": {"claims": {"sub": "student-sub-1"}},
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"planId": _PLAN_ID}),
    }


def test_checkout_in_progress_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_provider = MagicMock(spec=MockPayTabsAdapter)
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: mock_provider)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: {"blockReason": "checkout_in_progress"},
    )
    monkeypatch.setattr(billing_handler, "_invoke_billing_checkout_rollback", MagicMock())

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    body = json.loads(resp["body"])
    assert resp["statusCode"] == 409
    assert body["code"] == "checkout_in_progress"
    mock_provider.create_subscribe_session.assert_not_called()
