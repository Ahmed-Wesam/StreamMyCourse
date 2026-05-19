"""W7-P5 — billing edge POST /billing/reactivate-subscription."""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from catalog_invoke import CatalogInvokeError
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


def _reactivate_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/reactivate-subscription",
        "requestContext": {
            "resourcePath": "/billing/reactivate-subscription",
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
        "path": "/billing/reactivate-subscription",
        "requestContext": {"resourcePath": "/billing/reactivate-subscription"},
        "headers": {"Origin": "https://student.example.com"},
    }


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


def test_reactivate_subscription_options_returns_204_with_cors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    resp = billing_handler.lambda_handler(_options_event(), None)
    assert resp["statusCode"] == 204
    assert resp["headers"]["Access-Control-Allow-Origin"] == "https://student.example.com"
    assert "POST" in resp["headers"]["Access-Control-Allow-Methods"]


def test_reactivate_subscription_returns_401_without_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    evt = _reactivate_event()
    evt["requestContext"] = {"resourcePath": "/billing/reactivate-subscription"}

    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_reactivate_subscription_returns_503_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: None)

    resp = billing_handler.lambda_handler(_reactivate_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


def test_reactivate_subscription_returns_503_when_catalog_arn_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch, catalog_lambda_arn=None)

    resp = billing_handler.lambda_handler(_reactivate_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


def test_reactivate_subscription_returns_503_on_catalog_invoke_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_reactivate_prepare",
        MagicMock(side_effect=CatalogInvokeError("down")),
    )

    resp = billing_handler.lambda_handler(_reactivate_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


@pytest.mark.parametrize(
    "error_code",
    ["cannot_reactivate", "not_subscribed"],
)
def test_reactivate_subscription_maps_catalog_error_to_409(
    monkeypatch: pytest.MonkeyPatch,
    error_code: str,
) -> None:
    adapter = _patch_provider(monkeypatch)
    resume_calls: List[str] = []
    adapter.resume_agreement = MagicMock(side_effect=lambda agreement_id: resume_calls.append(agreement_id))  # type: ignore[method-assign]
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_reactivate_prepare",
        lambda **_kw: {"errorCode": error_code},
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_reactivate",
        MagicMock(side_effect=AssertionError("reactivate must not run after prepare error")),
    )

    resp = billing_handler.lambda_handler(_reactivate_event(), None)
    assert resp["statusCode"] == 409
    assert _parse_body(resp)["code"] == error_code
    assert resume_calls == []


def test_reactivate_subscription_returns_200_and_calls_resume_before_rds_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _patch_provider(monkeypatch)
    resume_calls: List[str] = []
    adapter.resume_agreement = MagicMock(side_effect=lambda agreement_id: resume_calls.append(agreement_id))  # type: ignore[method-assign]

    invoke_order: List[str] = []

    def _prepare(*, user_sub: str, catalog_lambda_arn: str) -> Dict[str, Any]:
        invoke_order.append("prepare")
        return {"providerSubscriptionId": _PROVIDER_SUB_ID}

    def _reactivate(*, user_sub: str, catalog_lambda_arn: str) -> Dict[str, Any]:
        invoke_order.append("reactivate")
        assert resume_calls == [_PROVIDER_SUB_ID]
        return {
            "status": "active",
            "cancelAtPeriodEnd": False,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        }

    monkeypatch.setattr(billing_handler, "_invoke_billing_reactivate_prepare", _prepare)
    monkeypatch.setattr(billing_handler, "_invoke_billing_reactivate", _reactivate)

    resp = billing_handler.lambda_handler(_reactivate_event(), None)
    assert resp["statusCode"] == 200
    body = _parse_body(resp)
    assert body == {
        "status": "active",
        "cancelAtPeriodEnd": False,
        "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
    }
    assert invoke_order == ["prepare", "reactivate"]
    assert resume_calls == [_PROVIDER_SUB_ID]


def test_reactivate_subscription_skips_resume_when_no_provider_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = _patch_provider(monkeypatch)
    resume_calls: List[str] = []
    adapter.resume_agreement = MagicMock(side_effect=lambda agreement_id: resume_calls.append(agreement_id))  # type: ignore[method-assign]
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_reactivate_prepare",
        lambda **_kw: {},
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_reactivate",
        lambda **_kw: {
            "status": "active",
            "cancelAtPeriodEnd": False,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        },
    )

    resp = billing_handler.lambda_handler(_reactivate_event(), None)
    assert resp["statusCode"] == 200
    assert resume_calls == []
