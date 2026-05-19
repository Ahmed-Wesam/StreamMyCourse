"""W6-P3 — PayTabs HPP payment/request payload (mocked HTTP)."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import patch

import pytest

from providers.paytabs_adapter import BillingUnconfiguredError, PayTabsAdapter
from providers.port import CheckoutPlan

_PLAN = CheckoutPlan(amount_minor=50000, currency="JOD", plan_key="monthly_all_access")
_USER_SUB = "cognito-sub-abc"
_PLAN_ID = "a0000000-0000-4000-8000-000000000011"
_SUCCESS_URL = "https://student.example.com/billing/success"
_CANCEL_URL = "https://student.example.com/billing/cancel"


def _adapter() -> PayTabsAdapter:
    return PayTabsAdapter(
        server_key="sk-test",
        profile_id="987654",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
        return_success_url=_SUCCESS_URL,
        return_cancel_url=_CANCEL_URL,
    )


def test_create_subscribe_session_builds_cart_id_and_amount() -> None:
    adapter = _adapter()
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        captured["url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return BytesIO(
            json.dumps({"redirect_url": "https://secure-jordan.paytabs.com/payment/page/abc"}).encode(
                "utf-8"
            )
        )

    with patch("providers.paytabs_adapter.urlopen", side_effect=fake_urlopen):
        result = adapter.create_subscribe_session(
            user_sub=_USER_SUB,
            plan_id=_PLAN_ID,
            plan=_PLAN,
        )

    assert result.redirect_url.startswith("https://")
    assert captured["url"] == "https://secure-jordan.paytabs.com/payment/request"
    body = captured["body"]
    assert body["cart_id"] == f"v1|dev|{_USER_SUB}|{_PLAN_ID}"
    assert body["cart_amount"] == 50.0
    assert body["cart_currency"] == "JOD"
    assert body["return"] == _SUCCESS_URL
    assert body["callback"] == _CANCEL_URL
    assert body["profile_id"] == 987654
    assert body["tran_type"] == "sale"
    assert body["tran_class"] == "ecom"


def test_create_subscribe_session_ignores_client_return_url_override() -> None:
    adapter = _adapter()

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        body = json.loads(req.data.decode("utf-8"))
        assert body["return"] == _SUCCESS_URL
        assert body["callback"] == _CANCEL_URL
        return BytesIO(json.dumps({"redirect_url": "https://paytabs.example/hpp"}).encode("utf-8"))

    with patch("providers.paytabs_adapter.urlopen", side_effect=fake_urlopen):
        adapter.create_subscribe_session(
            user_sub=_USER_SUB,
            plan_id=_PLAN_ID,
            plan=_PLAN,
            return_url="https://evil.example/phish",
        )


def test_create_subscribe_session_raises_when_keys_missing() -> None:
    adapter = PayTabsAdapter(
        server_key="",
        profile_id="",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
        return_success_url=_SUCCESS_URL,
        return_cancel_url=_CANCEL_URL,
    )
    with pytest.raises(BillingUnconfiguredError):
        adapter.create_subscribe_session(
            user_sub=_USER_SUB,
            plan_id=_PLAN_ID,
            plan=_PLAN,
        )
