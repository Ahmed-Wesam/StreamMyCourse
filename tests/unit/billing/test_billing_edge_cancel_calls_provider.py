"""W8-P1 — billing edge cancel calls provider.cancel_agreement after catalog success."""

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


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def _patch_provider(
    monkeypatch: pytest.MonkeyPatch,
    *,
    provider: MockPayTabsAdapter | None = None,
    **config_overrides: Any,
) -> MockPayTabsAdapter:
    adapter = provider or MockPayTabsAdapter(allow_mock_signature=True)
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config(**config_overrides))
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    return adapter


def test_cancel_subscription_calls_cancel_agreement_after_catalog_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _patch_provider(monkeypatch)
    cancel_calls: List[str] = []
    adapter.cancel_agreement = MagicMock(  # type: ignore[method-assign]
        side_effect=lambda agreement_id: cancel_calls.append(agreement_id)
    )

    catalog_payload = {
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
    body = _parse_body(resp)
    assert body == {
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
    }
    assert cancel_calls == [_PROVIDER_SUB_ID]
