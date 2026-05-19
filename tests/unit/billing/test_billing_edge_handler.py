"""P4 / W3-P4 — billing_edge HTTP handler (API Gateway proxy events)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_handler
from domain.events import BillingDomainEvent
from edge_config import BillingEdgeConfig
from providers.mock_adapter import MOCK_IPN_SALE_ACTIVATED, MockPayTabsAdapter
from providers.paytabs_adapter import BillingUnconfiguredError, PayTabsAdapter
from queue_shim import EnqueueError

_QUEUE_URL = "https://sqs.eu-west-1.amazonaws.com/1/test-queue"
_PLAN_ID = "00000000-0000-4000-8000-000000000001"
_DEFAULT_PLAN_ID = "a0000000-0000-4000-8000-000000000011"


def _edge_config(**overrides: Any) -> BillingEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "payment_provider": "mock",
        "paytabs_use_mock": True,
        "paytabs_secret_arn": None,
        "paytabs_server_key": None,
        "paytabs_profile_id": None,
        "paytabs_api_domain": None,
        "fulfillment_queue_url": _QUEUE_URL,
        "catalog_lambda_arn": "arn:aws:lambda:eu-west-1:1:function:catalog",
        "subscription_plan_id": _DEFAULT_PLAN_ID,
        "billing_return_success_url": "https://student.example.com/billing/success",
        "billing_return_cancel_url": "https://student.example.com/billing/cancel",
    }
    base.update(overrides)
    return BillingEdgeConfig(**base)


def _catalog_ok(**overrides: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "blockReason": None,
        "plan": {
            "amount_minor": 50000,
            "currency": "JOD",
            "plan_key": "monthly_all_access",
        },
    }
    payload.update(overrides)
    return payload


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
    request_id: str = "req-test-1",
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
            "requestId": request_id,
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


def _patch_mock_webhook(
    monkeypatch: pytest.MonkeyPatch,
    *,
    enqueue: MagicMock | None = None,
    config: BillingEdgeConfig | None = None,
) -> MagicMock:
    cfg = config or _edge_config()
    enqueue_fn = enqueue if enqueue is not None else MagicMock()
    monkeypatch.setattr(billing_handler, "_load_config", lambda: cfg)
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )
    monkeypatch.setattr(billing_handler, "_enqueue_domain_events", enqueue_fn)
    return enqueue_fn


def test_checkout_returns_503_billing_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: _edge_config(payment_provider=None, paytabs_use_mock=False),
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: None)

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 503
    body = _parse_body(resp)
    assert body["code"] == "billing_unconfigured"


def test_checkout_returns_401_without_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )
    evt = _checkout_event()
    evt["requestContext"] = {"resourcePath": "/billing/checkout-session"}

    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "unauthorized"


def test_checkout_empty_body_uses_subscription_plan_id_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: Dict[str, str] = {}
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: MockPayTabsAdapter(allow_mock_signature=True),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda *, user_sub, plan_id, catalog_lambda_arn: captured.update(
            {"user_sub": user_sub, "plan_id": plan_id, "arn": catalog_lambda_arn}
        )
        or _catalog_ok(),
    )

    evt = _checkout_event(body="")
    resp = billing_handler.lambda_handler(evt, None)
    assert resp["statusCode"] == 200
    assert captured["plan_id"] == _DEFAULT_PLAN_ID
    assert captured["user_sub"] == "student-sub-1"


def test_checkout_paytabs_missing_return_urls_skips_catalog_invoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoked = False
    adapter = PayTabsAdapter(
        server_key="server-key",
        profile_id="profile",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
        return_success_url=None,
        return_cancel_url=None,
    )

    def _invoke(**_kw: Any) -> Dict[str, Any]:
        nonlocal invoked
        invoked = True
        return _catalog_ok()

    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: _edge_config(
            payment_provider="paytabs",
            paytabs_use_mock=False,
            paytabs_server_key="server-key",
            paytabs_profile_id="profile",
            billing_return_success_url=None,
            billing_return_cancel_url=None,
        ),
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    monkeypatch.setattr(billing_handler, "_invoke_billing_checkout", _invoke)

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"
    assert invoked is False


def test_checkout_not_implemented_invokes_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback_calls: list[str] = []

    class NotImplementedProvider(MockPayTabsAdapter):
        def create_subscribe_session(self, **kwargs: Any) -> Any:
            raise NotImplementedError()

    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: NotImplementedProvider(allow_mock_signature=True),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: _catalog_ok(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout_rollback",
        lambda *, user_sub, catalog_lambda_arn: rollback_calls.append(user_sub),
    )

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 501
    assert rollback_calls == ["student-sub-1"]


def test_checkout_session_failure_invokes_rollback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rollback_calls: list[str] = []

    class FailingProvider(MockPayTabsAdapter):
        def create_subscribe_session(self, **kwargs: Any) -> Any:
            raise BillingUnconfiguredError()

    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(
        billing_handler,
        "_get_payment_provider",
        lambda _cfg: FailingProvider(allow_mock_signature=True),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: _catalog_ok(),
    )
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout_rollback",
        lambda *, user_sub, catalog_lambda_arn: rollback_calls.append(user_sub),
    )

    resp = billing_handler.lambda_handler(_checkout_event(), None)
    assert resp["statusCode"] == 503
    assert rollback_calls == ["student-sub-1"]


def test_checkout_mock_returns_200_with_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = MockPayTabsAdapter()
    monkeypatch.setattr(billing_handler, "_load_config", lambda: _edge_config())
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: mock)
    monkeypatch.setattr(
        billing_handler,
        "_invoke_billing_checkout",
        lambda **_kw: _catalog_ok(),
    )

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
        lambda: _edge_config(payment_provider=None, paytabs_use_mock=False),
    )

    resp = billing_handler.lambda_handler(_webhook_event(), None)
    assert resp["statusCode"] == 503
    assert _parse_body(resp)["code"] == "billing_unconfigured"


def test_webhook_mock_rejects_unsigned_with_401(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_webhook(monkeypatch)

    resp = billing_handler.lambda_handler(_webhook_event(), None)
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "invalid_signature"


def test_webhook_mock_valid_signature_returns_200_and_enqueues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enqueue = _patch_mock_webhook(monkeypatch)
    body = MockPayTabsAdapter.sample_ipn_bytes(MOCK_IPN_SALE_ACTIVATED)

    resp = billing_handler.lambda_handler(
        _webhook_event(body=body, mock_signature="test"),
        None,
    )
    assert resp["statusCode"] == 200
    assert _parse_body(resp) == {"status": "ok"}
    enqueue.assert_called_once()
    events: List[BillingDomainEvent] = enqueue.call_args[0][0]
    assert len(events) == 1
    assert events[0].event_type == "subscription.activated"
    assert events[0].provider_event_id == "paytabs:MOCK-ACT-001:A"


def test_webhook_mock_valid_signature_does_not_return_501(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_mock_webhook(monkeypatch)
    body = MockPayTabsAdapter.sample_ipn_bytes(MOCK_IPN_SALE_ACTIVATED)

    resp = billing_handler.lambda_handler(
        _webhook_event(body=body, mock_signature="test"),
        None,
    )
    assert resp["statusCode"] != 501
    body_json = _parse_body(resp)
    assert body_json.get("code") != "not_implemented"


def test_webhook_enqueue_failure_returns_500(monkeypatch: pytest.MonkeyPatch) -> None:
    enqueue = MagicMock(side_effect=EnqueueError("SQS down"))
    _patch_mock_webhook(monkeypatch, enqueue=enqueue)
    body = MockPayTabsAdapter.sample_ipn_bytes(MOCK_IPN_SALE_ACTIVATED)

    resp = billing_handler.lambda_handler(
        _webhook_event(body=body, mock_signature="test"),
        None,
    )
    assert resp["statusCode"] == 500
    assert _parse_body(resp)["code"] == "enqueue_failed"


def test_webhook_sale_missing_tran_ref_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_webhook(monkeypatch)
    body = MockPayTabsAdapter.sample_ipn_bytes(
        {
            "tran_type": "Sale",
            "payment_result": "A",
            "cart_id": f"v1|dev|mock-user-sub|{_PLAN_ID}",
            "transaction_time": "2026-05-18T12:00:00Z",
        }
    )
    resp = billing_handler.lambda_handler(
        _webhook_event(body=body, mock_signature="test"),
        None,
    )
    assert resp["statusCode"] == 400
    assert _parse_body(resp)["code"] == "invalid_cart_metadata"


def test_webhook_invalid_cart_metadata_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_webhook(monkeypatch)
    body = MockPayTabsAdapter.sample_ipn_bytes(
        {
            "tran_ref": "MOCK-BAD",
            "tran_type": "Sale",
            "payment_result": "A",
            "cart_id": "bad-metadata",
        }
    )
    resp = billing_handler.lambda_handler(
        _webhook_event(body=body, mock_signature="test"),
        None,
    )
    assert resp["statusCode"] == 400
    assert _parse_body(resp)["code"] == "invalid_cart_metadata"


def test_webhook_environment_mismatch_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_mock_webhook(monkeypatch)
    payload = dict(MOCK_IPN_SALE_ACTIVATED)
    payload["cart_id"] = f"v1|prod|mock-user-sub|{_PLAN_ID}"
    body = MockPayTabsAdapter.sample_ipn_bytes(payload)

    resp = billing_handler.lambda_handler(
        _webhook_event(body=body, mock_signature="test"),
        None,
    )
    assert resp["statusCode"] == 400
    assert _parse_body(resp)["code"] == "environment_mismatch"


def test_webhook_paytabs_invalid_signature_401(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = PayTabsAdapter(
        server_key="server-key",
        profile_id="profile",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
    )
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: _edge_config(
            payment_provider="paytabs",
            paytabs_use_mock=False,
            paytabs_server_key="server-key",
            paytabs_profile_id="profile",
            paytabs_api_domain="secure-jordan.paytabs.com",
        ),
    )
    monkeypatch.setattr(billing_handler, "_enqueue_domain_events", MagicMock())

    resp = billing_handler.lambda_handler(
        _webhook_event(body=b'{"x":1}', signature="bad-signature"),
        None,
    )
    assert resp["statusCode"] == 401
    assert _parse_body(resp)["code"] == "invalid_signature"


def test_webhook_paytabs_valid_signature_returns_200_not_501(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server_key = "server-key"
    raw = json.dumps(
        {
            "tran_ref": "TST1",
            "tran_type": "Sale",
            "payment_result": "A",
            "cart_id": f"v1|dev|student-sub-1|{_PLAN_ID}",
            "transaction_time": "2026-05-18T12:00:00Z",
        }
    ).encode("utf-8")
    sig = hmac.new(server_key.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    adapter = PayTabsAdapter(
        server_key=server_key,
        profile_id="profile",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
    )
    enqueue = MagicMock()
    monkeypatch.setattr(billing_handler, "_get_payment_provider", lambda _cfg: adapter)
    monkeypatch.setattr(
        billing_handler,
        "_load_config",
        lambda: _edge_config(
            payment_provider="paytabs",
            paytabs_use_mock=False,
            paytabs_server_key=server_key,
            paytabs_profile_id="profile",
            paytabs_api_domain="secure-jordan.paytabs.com",
        ),
    )
    monkeypatch.setattr(billing_handler, "_enqueue_domain_events", enqueue)

    resp = billing_handler.lambda_handler(_webhook_event(body=raw, signature=sig), None)
    assert resp["statusCode"] == 200
    assert _parse_body(resp)["status"] == "ok"
    enqueue.assert_called_once()
