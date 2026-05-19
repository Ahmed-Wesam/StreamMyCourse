"""W8-P2 — billing edge cancel: provider cancel_agreement failure after catalog success."""

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


def test_cancel_subscription_returns_502_when_provider_cancel_agreement_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _patch_provider(monkeypatch)
    catalog_calls: List[Dict[str, str]] = []
    catalog_payload = {
        "status": "canceled",
        "cancelAtPeriodEnd": True,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        "providerSubscriptionId": _PROVIDER_SUB_ID,
    }

    def _catalog_cancel(**kwargs: Any) -> Dict[str, Any]:
        catalog_calls.append(
            {
                "user_sub": str(kwargs.get("user_sub") or ""),
                "catalog_lambda_arn": str(kwargs.get("catalog_lambda_arn") or ""),
            }
        )
        return catalog_payload

    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_cancel_at_period_end",
        _catalog_cancel,
    )
    adapter.cancel_agreement = MagicMock(  # type: ignore[method-assign]
        side_effect=RuntimeError("PayTabs agreement cancel failed")
    )

    resp = billing_handler.lambda_handler(_cancel_event(), None)

    assert resp["statusCode"] == 502
    assert resp["statusCode"] != 200
    body = _parse_body(resp)
    assert body["code"] == "provider_cancel_failed"
    assert body["message"]
    assert catalog_calls == [
        {"user_sub": "student-sub-1", "catalog_lambda_arn": _CATALOG_ARN}
    ]
    adapter.cancel_agreement.assert_called_once_with(_PROVIDER_SUB_ID)  # type: ignore[attr-defined]


def test_cancel_subscription_returns_503_when_provider_missing_but_subscription_id_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
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

    resp = billing_handler._handle_cancel_subscription(  # noqa: SLF001
        _cancel_event(),
        None,
        _edge_config(),
    )

    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"
