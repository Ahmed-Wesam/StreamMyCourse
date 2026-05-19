"""W7-P5b — billing edge manage routes: JWT claims-only authz (no body override)."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from billing._imports import billing_handler
from catalog_invoke import (
    _INTERNAL_CANCEL_AT_PERIOD_END,
    _INTERNAL_REACTIVATE,
    _INTERNAL_REACTIVATE_PREPARE,
)
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockPayTabsAdapter

_CATALOG_ARN = "arn:aws:lambda:eu-west-1:1:function:catalog"
_JWT_SUB = "jwt-claims-sub"
_BODY_SUB = "body-override-sub"


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


def _patch_provider(monkeypatch: pytest.MonkeyPatch, **config_overrides: Any) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config(**config_overrides))
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )


def _manage_event(
    path: str,
    *,
    with_claims: bool = True,
    body: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": path,
        "requestContext": {
            "resourcePath": path,
            "stage": "dev",
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body or {}),
    }
    if with_claims:
        evt["requestContext"]["authorizer"] = {"claims": {"sub": _JWT_SUB}}
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def _mock_lambda_invoke_success(*, catalog_response: Dict[str, Any]) -> MagicMock:
    payload_bytes = json.dumps(catalog_response).encode("utf-8")
    mock_client = MagicMock()
    mock_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": BytesIO(payload_bytes),
    }
    return mock_client


def _mock_lambda_invoke_sequence(*responses: Dict[str, Any]) -> MagicMock:
    """Fresh Payload stream per invoke (reactivate calls catalog twice)."""
    pending: List[Dict[str, Any]] = list(responses)
    mock_client = MagicMock()

    def _invoke(**_kwargs: Any) -> Dict[str, Any]:
        if not pending:
            raise AssertionError("no more catalog responses configured")
        body = pending.pop(0)
        return {
            "StatusCode": 200,
            "Payload": BytesIO(json.dumps(body).encode("utf-8")),
        }

    mock_client.invoke.side_effect = _invoke
    return mock_client


@pytest.mark.parametrize(
    "path",
    ["/billing/cancel-subscription", "/billing/reactivate-subscription"],
)
def test_manage_route_returns_401_without_authorizer_claims(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    _patch_provider(monkeypatch)
    evt = _manage_event(path, with_claims=False)

    resp = billing_handler.lambda_handler(evt, None)

    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_cancel_subscription_catalog_invoke_uses_jwt_sub_not_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    captured_payloads: List[Dict[str, Any]] = []
    mock_client = _mock_lambda_invoke_success(
        catalog_response={
            "status": "canceled",
            "cancelAtPeriodEnd": True,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        },
    )

    def _capture_invoke(**kwargs: Any) -> Dict[str, Any]:
        raw = kwargs.get("Payload")
        assert raw is not None
        captured_payloads.append(json.loads(raw.decode("utf-8")))
        return mock_client.invoke.return_value

    mock_client.invoke.side_effect = _capture_invoke

    evt = _manage_event(
        "/billing/cancel-subscription",
        body={"userSub": _BODY_SUB, "user_sub": _BODY_SUB},
    )

    with patch("catalog_invoke.boto3.client", return_value=mock_client):
        resp = billing_handler.lambda_handler(evt, None)

    assert resp["statusCode"] == 200
    assert len(captured_payloads) == 1
    payload = captured_payloads[0]
    assert payload["userSub"] == _JWT_SUB
    assert payload["userSub"] != _BODY_SUB
    assert payload["internal"] == _INTERNAL_CANCEL_AT_PERIOD_END
    mock_client.invoke.assert_called_once()
    assert mock_client.invoke.call_args.kwargs["FunctionName"] == _CATALOG_ARN


def test_reactivate_subscription_catalog_invoke_uses_jwt_sub_not_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_provider(monkeypatch)
    captured_payloads: List[Dict[str, Any]] = []
    base_client = _mock_lambda_invoke_sequence(
        {"providerSubscriptionId": "AGR-100"},
        {
            "status": "active",
            "cancelAtPeriodEnd": False,
            "currentPeriodEnd": "2026-06-18T00:00:00.000Z",
        },
    )

    def _capture_invoke(**kwargs: Any) -> Dict[str, Any]:
        raw = kwargs.get("Payload")
        assert raw is not None
        captured_payloads.append(json.loads(raw.decode("utf-8")))
        return base_client.invoke(**kwargs)

    mock_client = MagicMock()
    mock_client.invoke.side_effect = _capture_invoke

    evt = _manage_event(
        "/billing/reactivate-subscription",
        body={"userSub": _BODY_SUB, "user_sub": _BODY_SUB},
    )

    with patch("catalog_invoke.boto3.client", return_value=mock_client):
        resp = billing_handler.lambda_handler(evt, None)

    assert resp["statusCode"] == 200
    assert len(captured_payloads) == 2
    prepare_payload, reactivate_payload = captured_payloads
    assert prepare_payload["userSub"] == _JWT_SUB
    assert prepare_payload["userSub"] != _BODY_SUB
    assert prepare_payload["internal"] == _INTERNAL_REACTIVATE_PREPARE
    assert reactivate_payload["userSub"] == _JWT_SUB
    assert reactivate_payload["userSub"] != _BODY_SUB
    assert reactivate_payload["internal"] == _INTERNAL_REACTIVATE
    assert mock_client.invoke.call_count == 2
    for call in mock_client.invoke.call_args_list:
        assert call.kwargs["FunctionName"] == _CATALOG_ARN
