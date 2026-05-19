"""WS8 — retry provider cancel when catalog returns already_canceled with agreement id."""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockPayTabsAdapter

_CATALOG_ARN = "arn:aws:lambda:eu-west-1:1:function:catalog"
_PROVIDER_SUB_ID = "AGR-100"


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


def _cancel_event() -> Dict[str, Any]:
    return {
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


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_cancel_subscription_retries_provider_on_already_canceled_with_agreement_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = MockPayTabsAdapter(allow_mock_signature=True)
    cancel_calls: List[str] = []
    adapter.cancel_agreement = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda agreement_id: cancel_calls.append(agreement_id)
    )
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    catalog_payload = {
        "errorCode": "already_canceled",
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        "providerSubscriptionId": _PROVIDER_SUB_ID,
    }
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        lambda **_kw: catalog_payload,
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)

    assert resp["statusCode"] == 200
    assert _parse_body(resp) == {
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
    }
    assert cancel_calls == [_PROVIDER_SUB_ID]


def test_cancel_subscription_returns_502_when_catalog_ok_without_provider_agreement_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = MockPayTabsAdapter(allow_mock_signature=True)
    adapter.cancel_agreement = MagicMock()  # type: ignore[method-assign]
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    catalog_payload = {
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
    }
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        lambda **_kw: catalog_payload,
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)

    assert resp["statusCode"] == 502
    assert _parse_body(resp)["code"] == "provider_agreement_missing"
    adapter.cancel_agreement.assert_not_called()  # type: ignore[attr-defined]


def test_cancel_subscription_returns_502_provider_agreement_missing_on_already_canceled_without_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = MockPayTabsAdapter(allow_mock_signature=True)
    adapter.cancel_agreement = MagicMock()  # type: ignore[method-assign]
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    catalog_payload = {
        "errorCode": "already_canceled",
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
    }
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        lambda **_kw: catalog_payload,
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)

    assert resp["statusCode"] == 502
    assert _parse_body(resp)["code"] == "provider_agreement_missing"
    adapter.cancel_agreement.assert_not_called()  # type: ignore[attr-defined]
