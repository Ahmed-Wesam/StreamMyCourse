"""W7-P5 — billing edge POST /billing/cancel-subscription."""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from catalog_invoke import CatalogInvokeError
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockPayTabsAdapter

_CATALOG_ARN = "arn:aws:lambda:eu-west-1:1:function:catalog"


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
        "subscription_plan_id": "a0000000-0000-4000-8000-000000000011",
        "billing_return_success_url": "https://student.example.com/billing/success",
        "billing_return_cancel_url": "https://student.example.com/billing/cancel",
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _cancel_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/cancel-subscription",
        "requestContext": {
            "resourcePath": "/billing/cancel-subscription",
            "stage": "dev",
            "authorizer": {"claims": {"sub": "student-sub-1"}},
        },
        "headers": {"content-type": "application/json"},
        "body": "{}",
    }
    evt.update(overrides)
    return evt


def _options_event() -> Dict[str, Any]:
    return {
        "httpMethod": "OPTIONS",
        "path": "/billing/cancel-subscription",
        "requestContext": {"resourcePath": "/billing/cancel-subscription"},
        "headers": {"Origin": "https://student.example.com"},
    }


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def _patch_provider(monkeypatch: pytest.MonkeyPatch, **config_overrides: Any) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config(**config_overrides))
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )


def test_cancel_subscription_options_returns_204_with_cors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    resp = billing_handler.lambda_handler(_options_event(), None)
    assert resp["statusCode"] == 204
    assert resp["headers"]["Access-Control-Allow-Origin"] == "https://student.example.com"
    assert "POST" in resp["headers"]["Access-Control-Allow-Methods"]


def test_cancel_subscription_returns_401_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    evt = _cancel_event()
    evt["requestContext"] = {"resourcePath": "/billing/cancel-subscription"}

    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_cancel_subscription_returns_503_when_catalog_arn_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch, catalog_lambda_arn=None)

    resp = billing_handler.lambda_handler(_cancel_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


def test_cancel_subscription_returns_503_on_catalog_invoke_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        MagicMock(side_effect=CatalogInvokeError("down")),
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


@pytest.mark.parametrize(
    "error_code",
    ["not_subscribed", "cannot_cancel"],
)
def test_cancel_subscription_maps_catalog_error_to_409(
    monkeypatch: pytest.MonkeyPatch,
    error_code: str,
) -> None:
    _patch_provider(monkeypatch)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        lambda **_kw: {"errorCode": error_code},
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)
    assert resp["statusCode"] == 409
    assert _parse_body(resp)["code"] == error_code


def test_cancel_subscription_returns_provider_agreement_missing_when_already_canceled_without_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        lambda **_kw: {
            "errorCode": "already_canceled",
            "status": "canceled",
            "cancelAtPeriodEnd": True,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        },
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)
    assert resp["statusCode"] == 502
    assert _parse_body(resp)["code"] == "provider_agreement_missing"


def test_cancel_subscription_returns_200_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    catalog_payload = {
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        "providerSubscriptionId": "AGR-100",
    }
    captured: Dict[str, str] = {}
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        lambda *, user_sub, catalog_lambda_arn: captured.update(
            {"user_sub": user_sub, "arn": catalog_lambda_arn}
        )
        or catalog_payload,
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)
    assert resp["statusCode"] == 200
    assert _parse_body(resp) == {
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
    }
    assert captured == {"user_sub": "student-sub-1", "arn": _CATALOG_ARN}
