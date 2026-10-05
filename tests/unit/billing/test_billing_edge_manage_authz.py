"""RS-5 — billing edge checkout route: JWT claims-only authz (no body override)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockHyperPayAdapter

_CATALOG_ARN = "arn:aws:lambda:eu-west-1:1:function:catalog"
_JWT_SUB = "jwt-claims-sub"
_BODY_SUB = "body-override-sub"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "mock",
        "hyperpay_secret_arn": None,
        "hyperpay_access_token": None,
        "hyperpay_entity_id": None,
        "hyperpay_webhook_secret": None,
        "fulfillment_queue_url": "https://sqs.eu-west-1.amazonaws.com/1/q",
        "catalog_lambda_arn": _CATALOG_ARN,
        "billing_shopper_result_url": "https://student.example.com/billing/result",
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _patch_provider(monkeypatch: pytest.MonkeyPatch, **config_overrides: Any) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config(**config_overrides))
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockHyperPayAdapter(),
    )


def _checkout_event(*, with_claims: bool = True) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "stage": "dev",
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "productType": "course",
                "courseId": _COURSE_ID,
                "userSub": _BODY_SUB,
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
    if with_claims:
        evt["requestContext"]["authorizer"] = {
            "claims": {"sub": _JWT_SUB, "email": "student@example.com"},
        }
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_checkout_session_returns_401_without_authorizer_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    resp = billing_handler.lambda_handler(_checkout_event(with_claims=False), None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_checkout_session_catalog_invoke_uses_jwt_sub_not_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    captured: list[Dict[str, Any]] = []

    def _capture(**kwargs: Any) -> Dict[str, Any]:
        captured.append(dict(kwargs))
        return {
            "blockReason": None,
            "product": {
                "amount_minor": 50_000,
                "currency": "JOD",
                "course_id": _COURSE_ID,
                "purchase_id": "c0000000-0000-4000-8000-000000000001",
            },
        }

    mock_provider = MagicMock()
    mock_provider.create_checkout.return_value = MagicMock(
        checkout_id="CHK-1",
        widget_url="https://mock.example/widget.js",
        integrity="sha384-x",
    )
    monkeypatch.setattr(billing_handler, "_invoke_billing_checkout", _capture)
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: mock_provider)

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 200
    assert len(captured) == 1
    assert captured[0]["user_sub"] == _JWT_SUB
    assert captured[0]["user_sub"] != _BODY_SUB
