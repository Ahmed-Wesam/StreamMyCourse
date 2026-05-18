"""P4 — billing_edge HTTP handler (API Gateway proxy events)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Dict

import pytest

from billing._imports import billing_handler
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MockPayTabsAdapter
from providers.paytabs_adapter import PayTabsAdapter


def _checkout_event(**overrides: Any) -> Dict[str, Any]:
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/billing/checkout-session",
        "requestContext": {
            "resourcePath": "/billing/checkout-session",
            "stage": "dev",
            "authorizer": {"claims": {"sub": "student-sub-1"}},
        },
        "headers": {"content-type": "application/json"},
        "body": json.dumps({"planId": "plan-monthly"}),
    }
    evt.update(overrides)
    return evt


def _webhook_event(
    *,
    body: bytes = b'{"tran_ref":"TST1"}',
    signature: str | None = None,
    mock_signature: str | None = None,
    is_base64: bool = False,
) -> Dict[str, Any]:
    headers: Dict[str, str] = {"content-type": "application/json"}
    if signature is not None:
        headers["Signature"] = signature
    if mock_signature is not None:
        headers["X-Mock-Signature"] = mock_signature
    evt: Dict[str, Any] = {
        "httpMethod": "POST",
        "path": "/webhooks/payments/paytabs",
        "requestContext": {
            "resourcePath": "/webhooks/payments/paytabs",
            "stage": "dev",
        },
        "headers": headers,
        "isBase64Encoded": is_base64,
    }
    if is_base64:
        evt["body"] = base64.b64encode(body).decode("ascii")
    else:
        evt["body"] = body.decode("utf-8")
    return evt


def _parse_body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_checkout_returns_503_billing_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: BillingEdgeConfig(
            deployment_environment="dev",
            payment_provider=None,
            paytabs_use_mock=False,
            paytabs_secret_arn=None,
            paytabs_server_key=None,
            paytabs_profile_id=None,
            paytabs_api_domain=None,
        ),
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: None)

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 503
    body = _parse_body(resp)
    assert body["code"] == "billing_unconfigured"


def test_checkout_mock_returns_200_with_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = MockPayTabsAdapter()
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: BillingEdgeConfig(
            deployment_environment="dev",
            payment_provider="mock",
            paytabs_use_mock=True,
            paytabs_secret_arn=None,
            paytabs_server_key=None,
            paytabs_profile_id=None,
            paytabs_api_domain=None,
        ),
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: mock)

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 200
    body = _parse_body(resp)
    assert "redirect_url" in body
    assert body["redirect_url"].startswith("https://")


def test_webhook_returns_503_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: None)
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: BillingEdgeConfig(
            deployment_environment="dev",
            payment_provider=None,
            paytabs_use_mock=False,
            paytabs_secret_arn=None,
            paytabs_server_key=None,
            paytabs_profile_id=None,
            paytabs_api_domain=None,
        ),
    )

    resp = billing_handler.lambda_handler(_webhook_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


def test_webhook_mock_rejects_unsigned_with_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: BillingEdgeConfig(
            deployment_environment="dev",
            payment_provider="mock",
            paytabs_use_mock=True,
            paytabs_secret_arn=None,
            paytabs_server_key=None,
            paytabs_profile_id=None,
            paytabs_api_domain=None,
        ),
    )

    resp = billing_handler.lambda_handler(_webhook_event(), None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "invalid_signature"


def test_webhook_mock_valid_signature_returns_501_not_implemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: BillingEdgeConfig(
            deployment_environment="dev",
            payment_provider="mock",
            paytabs_use_mock=True,
            paytabs_secret_arn=None,
            paytabs_server_key=None,
            paytabs_profile_id=None,
            paytabs_api_domain=None,
        ),
    )

    resp = billing_handler.lambda_handler(_webhook_event(mock_signature="test"), None)
    assert resp["statusCode"] == 501
    assert _parse_body(resp)["code"] == "not_implemented"


def test_webhook_paytabs_invalid_signature_401(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = PayTabsAdapter(
        server_key="server-key",
        profile_id="profile",
        api_domain="secure-jordan.paytabs.com",
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: BillingEdgeConfig(
            deployment_environment="dev",
            payment_provider="paytabs",
            paytabs_use_mock=False,
            paytabs_secret_arn=None,
            paytabs_server_key="server-key",
            paytabs_profile_id="profile",
            paytabs_api_domain="secure-jordan.paytabs.com",
        ),
    )

    resp = billing_handler.lambda_handler(
        _webhook_event(body=b'{"x":1}', signature="bad-signature"),
        None,
    )
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "invalid_signature"


def test_webhook_paytabs_valid_signature_returns_501(monkeypatch: pytest.MonkeyPatch) -> None:
    server_key = "server-key"
    raw = b'{"tran_ref":"TST1"}'
    sig = hmac.new(server_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    adapter = PayTabsAdapter(
        server_key=server_key,
        profile_id="profile",
        api_domain="secure-jordan.paytabs.com",
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: BillingEdgeConfig(
            deployment_environment="dev",
            payment_provider="paytabs",
            paytabs_use_mock=False,
            paytabs_secret_arn=None,
            paytabs_server_key=server_key,
            paytabs_profile_id="profile",
            paytabs_api_domain="secure-jordan.paytabs.com",
        ),
    )

    resp = billing_handler.lambda_handler(_webhook_event(body=raw, signature=sig), None)
    assert resp["statusCode"] == 501
    assert _parse_body(resp)["code"] == "not_implemented"
