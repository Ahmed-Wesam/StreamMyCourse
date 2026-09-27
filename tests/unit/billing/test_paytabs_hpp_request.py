"""W6-P3 / RS-5 — PayTabs HPP payment/request payload (mocked HTTP)."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import patch

import pytest

from providers.paytabs_adapter import BillingUnconfiguredError, PayTabsAdapter
from providers.port import CheckoutProduct

_USER_SUB = "cognito-sub-abc"
_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"
_PRODUCT = CheckoutProduct(amount_minor=9900, currency="USD", description="course")
_SUCCESS_URL = "https://student.example.com/billing/success"
_IPN_URL = "https://api.example.com/webhooks/payments/paytabs"


def _adapter() -> PayTabsAdapter:
    return PayTabsAdapter(
        server_key="sk-test",
        profile_id="987654",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
        return_success_url=_SUCCESS_URL,
        ipn_callback_url=_IPN_URL,
    )


def test_create_sale_session_builds_cart_id_and_usd_amount() -> None:
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
        result = adapter.create_sale_session(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="course",
            course_id=_COURSE_ID,
            product=_PRODUCT,
        )

    assert result.redirect_url.startswith("https://")
    assert captured["url"] == "https://secure-jordan.paytabs.com/payment/request"
    body = captured["body"]
    assert body["cart_id"] == f"v2|dev|{_USER_SUB}|course|{_COURSE_ID}|{_PURCHASE_ID}"
    assert body["cart_amount"] == 99.0
    assert body["cart_currency"] == "USD"
    assert body["return"] == _SUCCESS_URL
    assert body["callback"] == _IPN_URL
    assert body["profile_id"] == 987654
    assert body["tran_type"] == "sale"
    assert body["tran_class"] == "ecom"


def test_create_sale_session_rejects_untrusted_redirect_host() -> None:
    adapter = _adapter()

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        return BytesIO(json.dumps({"redirect_url": "https://evil.example/phish"}).encode("utf-8"))

    with patch("providers.paytabs_adapter.urlopen", side_effect=fake_urlopen):
        with pytest.raises(BillingUnconfiguredError):
            adapter.create_sale_session(
                user_sub=_USER_SUB,
                purchase_id=_PURCHASE_ID,
                product_type="bundle",
                course_id=None,
                product=CheckoutProduct(amount_minor=15000, currency="USD", description="bundle"),
            )


def test_create_sale_session_accepts_mock_paytabs_redirect_host() -> None:
    adapter = _adapter()

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        return BytesIO(
            json.dumps({"redirect_url": "https://mock.paytabs.example/checkout/session"}).encode(
                "utf-8"
            )
        )

    with patch("providers.paytabs_adapter.urlopen", side_effect=fake_urlopen):
        result = adapter.create_sale_session(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="bundle",
            course_id=None,
            product=CheckoutProduct(amount_minor=15000, currency="USD", description="bundle"),
        )
    assert "mock.paytabs.example" in result.redirect_url


def test_create_sale_session_raises_when_keys_missing() -> None:
    adapter = PayTabsAdapter(
        server_key="",
        profile_id="",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
        return_success_url=_SUCCESS_URL,
        ipn_callback_url=_IPN_URL,
    )
    with pytest.raises(BillingUnconfiguredError):
        adapter.create_sale_session(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="course",
            course_id=_COURSE_ID,
            product=_PRODUCT,
        )
