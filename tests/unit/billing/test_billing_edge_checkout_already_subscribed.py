"""RS-5 — checkout returns 409 already_owned when catalog blocks."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockHyperPayAdapter

_COURSE_ID = "b0000000-0000-4000-8000-000000000001"


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "mock",
        "hyperpay_secret_arn": None,
        "hyperpay_access_token": None,
        "hyperpay_entity_id": None,
        "hyperpay_webhook_secret": None,
        "fulfillment_queue_url": "https://sqs.example.com/q",
        "catalog_lambda_arn": "arn:aws:lambda:eu-west-1:1:function:catalog",
        "billing_shopper_result_url": "https://student.example.com/billing/result",
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _checkout_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
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
    evt.update(overrides)
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_checkout_already_owned_returns_409(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockHyperPayAdapter(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: {"blockReason": "already_owned"},
    )

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 409
    body = _parse_body(resp)
    assert body["code"] == "already_owned"
    assert body["message"]


def test_checkout_already_owned_does_not_call_hyperpay_checkout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_provider = MagicMock()
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: mock_provider)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: {"blockReason": "already_owned"},
    )

    billing_handler.lambda_handler(_checkout_event(), None)
    mock_provider.create_checkout.assert_not_called()
