"""RS-5 — billing edge checkout route: JWT claims-only authz (no body override)."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockPayTabsAdapter

_CATALOG_ARN = "arn:aws:lambda:eu-west-1:1:function:catalog"
_JWT_SUB = "jwt-claims-sub"
_BODY_SUB = "body-override-sub"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "mock",
        "paytabs_use_mock": True,
        "paytabs_secret_arn": None,
        "paytabs_server_key": None,
        "paytabs_profile_id": None,
        "paytabs_api_domain": None,
        "fulfillment_queue_url": "https://sqs.eu-west-1.amazonaws.com/1/q",
        "catalog_lambda_arn": _CATALOG_ARN,
        "billing_return_success_url": "https://student.example.com/billing/success",
        "billing_return_cancel_url": "https://student.example.com/billing/cancel",
        "billing_ipn_callback_url": "https://api.example.com/webhooks/payments/paytabs",
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _patch_provider(monkeypatch: pytest.MonkeyPatch, **config_overrides: Any) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config(**config_overrides))
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
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
            {"productType": "course", "courseId": _COURSE_ID, "userSub": _BODY_SUB}
        ),
    }
    if with_claims:
        evt["requestContext"]["authorizer"] = {"claims": {"sub": _JWT_SUB}}
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
                "amount_minor": 9900,
                "currency": "USD",
                "course_id": _COURSE_ID,
                "purchase_id": "c0000000-0000-4000-8000-000000000001",
            },
        }

    mock_provider = MagicMock()
    mock_provider.create_sale_session.return_value = MagicMock(redirect_url="https://pay.example/hpp")
    monkeypatch.setattr(billing_handler, "_invoke_billing_checkout", _capture)
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: mock_provider)

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 200
    assert len(captured) == 1
    assert captured[0]["user_sub"] == _JWT_SUB
    assert captured[0]["user_sub"] != _BODY_SUB
