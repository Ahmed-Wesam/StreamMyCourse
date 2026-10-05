"""W6 — checkout returns 409 checkout_in_progress when catalog blocks fresh incomplete."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockHyperPayAdapter

_CATALOG_ARN = "arn:aws:lambda:eu-west-1:1:function:catalog"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"


def _edge_config() -> BillingEdgeConfig:
    return BillingEdgeConfig(
        deployment_environment="dev",
        payment_provider="mock",
        hyperpay_secret_arn=None,
        hyperpay_access_token=None,
        hyperpay_entity_id=None,
        hyperpay_webhook_secret=None,
        fulfillment_queue_url="https://sqs.eu-west-1.amazonaws.com/1/q",
        catalog_lambda_arn=_CATALOG_ARN,
        billing_shopper_result_url="https://student.example.com/billing/result",
    )


def _checkout_event() -> Dict[str, Any]:
    return {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "authorizer": {
                "claims": {"sub": "student-sub-1", "email": "student@example.com"},
            },
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "productType": "course",
                "courseId": _COURSE_ID,
                "billing": {
                    "givenName": "Ada",
                    "surname": "Student",
                    "street": "1 King Hussein St",
                    "city": "Amman",
                    "state": "Amman",
                    "postcode": "11118",
                    "country": "JO",
                },
            }
        ),
    }


def test_checkout_in_progress_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_provider = MagicMock(spec=MockHyperPayAdapter)
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
    mock_provider.create_checkout.assert_not_called()
