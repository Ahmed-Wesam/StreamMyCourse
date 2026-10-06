"""HyperPay checkout adapter (mocked urllib HTTP)."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs

import pytest

from domain.checkout_billing import CheckoutBillingContact
from providers.hyperpay_adapter import (
    BillingUnconfiguredError,
    HyperPayAdapter,
    clear_checkout_poll_cache,
    parse_checkout_payment_poll,
)
from providers.port import CheckoutProduct

@pytest.fixture(autouse=True)
def _clear_hyperpay_poll_cache() -> None:
    clear_checkout_poll_cache()
    yield
    clear_checkout_poll_cache()


_USER_SUB = "cognito-sub-abc"
_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"
_PRODUCT = CheckoutProduct(amount_minor=50_000, currency="JOD", description="course")
_SHOPPER_RESULT_URL = "https://student.example.com/billing/hyperpay/return"
_BILLING = CheckoutBillingContact(
    given_name="Ada",
    surname="Student",
    street="1 King Hussein St",
    city="Amman",
    state="Amman",
    postcode="11118",
    country="JO",
)
_CUSTOMER_EMAIL = "student@example.com"


def _adapter(*, api_host: str = "eu-test.oppwa.com") -> HyperPayAdapter:
    return HyperPayAdapter(
        access_token="access-token-test",
        entity_id="entity-id-test",
        api_host=api_host,
        deployment_environment="dev",
        shopper_result_url=_SHOPPER_RESULT_URL,
    )


def test_create_checkout_posts_form_body_with_bearer_and_integrity() -> None:
    adapter = _adapter()
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        captured["url"] = req.full_url
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        captured["body"] = parse_qs(req.data.decode("utf-8"))
        return BytesIO(
            json.dumps(
                {
                    "id": "CHECKOUT-ID-1",
                    "integrity": "sha384-abc",
                }
            ).encode("utf-8")
        )

    with patch("providers.hyperpay_adapter.urlopen", side_effect=fake_urlopen):
        result = adapter.create_checkout(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="course",
            course_id=_COURSE_ID,
            product=_PRODUCT,
            customer_email=_CUSTOMER_EMAIL,
            billing=_BILLING,
        )

    assert captured["url"] == "https://eu-test.oppwa.com/v1/checkouts"
    assert captured["headers"]["authorization"] == "Bearer access-token-test"
    assert captured["headers"]["content-type"].startswith(
        "application/x-www-form-urlencoded"
    )
    body = captured["body"]
    assert body["entityId"] == ["entity-id-test"]
    assert body["amount"] == ["50.00"]
    assert body["currency"] == ["JOD"]
    assert body["paymentType"] == ["DB"]
    assert body["integrity"] == ["true"]
    assert body["testMode"] == ["EXTERNAL"]
    cart_id = f"v2|dev|{_USER_SUB}|course|{_COURSE_ID}|{_PURCHASE_ID}"
    assert body["merchantTransactionId"] == [cart_id]
    assert body["shopperResultUrl"] == [_SHOPPER_RESULT_URL]
    assert body["customer.email"] == [_CUSTOMER_EMAIL]
    assert body["customer.givenName"] == ["Ada"]
    assert body["billing.country"] == ["JO"]
    assert body["customParameters[3DS2_enrolled]"] == ["true"]
    assert body["customParameters[SHOPPER_cart]"] == [cart_id]
    assert (
        result.widget_url
        == "https://eu-test.oppwa.com/v1/paymentWidgets.js?checkoutId=CHECKOUT-ID-1"
    )
    assert result.checkout_id == "CHECKOUT-ID-1"
    assert result.integrity == "sha384-abc"


def test_create_checkout_omits_test_mode_on_production_host() -> None:
    adapter = _adapter(api_host="eu-prod.oppwa.com")
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        captured["body"] = parse_qs(req.data.decode("utf-8"))
        return BytesIO(json.dumps({"id": "CHK-PROD", "integrity": "sha384-x"}).encode("utf-8"))

    with patch("providers.hyperpay_adapter.urlopen", side_effect=fake_urlopen):
        adapter.create_checkout(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="bundle",
            course_id=None,
            product=CheckoutProduct(amount_minor=150_000, currency="JOD", description="bundle"),
            customer_email=_CUSTOMER_EMAIL,
            billing=_BILLING,
        )

    assert "testMode" not in captured["body"]


def test_create_checkout_rejects_non_whole_jod_amount() -> None:
    adapter = _adapter()
    with pytest.raises(ValueError, match="whole JOD"):
        adapter.create_checkout(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="course",
            course_id=_COURSE_ID,
            product=CheckoutProduct(amount_minor=50_500, currency="JOD", description="x"),
            customer_email=_CUSTOMER_EMAIL,
            billing=_BILLING,
        )


def test_create_checkout_rejects_untrusted_widget_host() -> None:
    adapter = HyperPayAdapter(
        access_token="access-token-test",
        entity_id="entity-id-test",
        api_host="evil.example.com",
        deployment_environment="dev",
        shopper_result_url=_SHOPPER_RESULT_URL,
    )

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        return BytesIO(json.dumps({"id": "EVIL", "integrity": "x"}).encode("utf-8"))

    with patch("providers.hyperpay_adapter.urlopen", side_effect=fake_urlopen):
        with pytest.raises(BillingUnconfiguredError):
            adapter.create_checkout(
                user_sub=_USER_SUB,
                purchase_id=_PURCHASE_ID,
                product_type="course",
                course_id=_COURSE_ID,
                product=_PRODUCT,
                customer_email=_CUSTOMER_EMAIL,
                billing=_BILLING,
            )


def test_create_checkout_accepts_mock_hyperpay_widget_host() -> None:
    adapter = _adapter(api_host="mock.hyperpay.example")

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        return BytesIO(json.dumps({"id": "MOCK-1", "integrity": "x"}).encode("utf-8"))

    with patch("providers.hyperpay_adapter.urlopen", side_effect=fake_urlopen):
        result = adapter.create_checkout(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="course",
            course_id=_COURSE_ID,
            product=_PRODUCT,
            customer_email=_CUSTOMER_EMAIL,
            billing=_BILLING,
        )
    assert "mock.hyperpay.example" in result.widget_url


def test_create_checkout_raises_when_credentials_missing() -> None:
    adapter = HyperPayAdapter(
        access_token="",
        entity_id="",
        api_host="eu-test.oppwa.com",
        deployment_environment="dev",
        shopper_result_url=_SHOPPER_RESULT_URL,
    )
    with pytest.raises(BillingUnconfiguredError):
        adapter.create_checkout(
            user_sub=_USER_SUB,
            purchase_id=_PURCHASE_ID,
            product_type="course",
            course_id=_COURSE_ID,
            product=_PRODUCT,
            customer_email=_CUSTOMER_EMAIL,
            billing=_BILLING,
        )


def test_parse_checkout_poll_rate_limit_is_pending() -> None:
    status, events = parse_checkout_payment_poll(
        {
            "result": {
                "code": "800.120.100",
                "description": "Too many requests. Please try again later.",
            }
        },
        deployment_environment="prod",
    )
    assert status == "pending"
    assert events == []


def test_parse_checkout_poll_no_payment_session_is_pending() -> None:
    status, events = parse_checkout_payment_poll(
        {
            "result": {
                "code": "200.300.404",
                "description": "No payment session found for the requested id",
            }
        },
        deployment_environment="prod",
    )
    assert status == "pending"
    assert events == []


def test_parse_checkout_poll_failed_without_merchant_tx_returns_failed() -> None:
    status, events = parse_checkout_payment_poll(
        {"result": {"code": "100.380.401", "description": "declined"}},
        deployment_environment="prod",
    )
    assert status == "failed"
    assert events == []


def test_parse_checkout_poll_uses_shopper_cart_custom_parameter() -> None:
    cart = f"v2|prod|{_USER_SUB}|course|{_COURSE_ID}|{_PURCHASE_ID}"
    status, events = parse_checkout_payment_poll(
        {
            "id": "PAY-9",
            "amount": "50.00",
            "currency": "JOD",
            "result": {"code": "000.000.000"},
            "customParameters": {"SHOPPER_cart": cart},
        },
        deployment_environment="prod",
    )
    assert status == "success"
    assert len(events) == 1
    assert events[0].purchase_id == _PURCHASE_ID


def test_fetch_checkout_result_debounces_pending_polls() -> None:
    clear_checkout_poll_cache()
    adapter = _adapter()
    calls = {"n": 0}

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        from urllib.error import HTTPError

        calls["n"] += 1
        body = json.dumps(
            {
                "result": {
                    "code": "200.300.404",
                    "description": "No payment session found",
                }
            }
        ).encode("utf-8")
        raise HTTPError(req.full_url, 400, "Bad Request", hdrs=None, fp=BytesIO(body))

    with patch("providers.hyperpay_adapter.urlopen", side_effect=fake_urlopen):
        adapter.fetch_checkout_result("CHECKOUT-DEBOUNCE")
        adapter.fetch_checkout_result("CHECKOUT-DEBOUNCE")

    assert calls["n"] == 1


def test_fetch_checkout_result_parses_http_400_json_body() -> None:
    adapter = _adapter()

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        from urllib.error import HTTPError

        body = json.dumps(
            {
                "result": {
                    "code": "200.300.404",
                    "description": "No payment session found",
                }
            }
        ).encode("utf-8")
        raise HTTPError(req.full_url, 400, "Bad Request", hdrs=None, fp=BytesIO(body))

    with patch("providers.hyperpay_adapter.urlopen", side_effect=fake_urlopen):
        payload = adapter.fetch_checkout_result("CHECKOUT-ID-1")

    assert payload["result"]["code"] == "200.300.404"


def test_fetch_checkout_result_uses_bearer_get() -> None:
    adapter = _adapter()
    captured: dict[str, Any] = {}

    def fake_urlopen(req: Any, timeout: float = 0) -> Any:
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["headers"] = {k.lower(): v for k, v in req.header_items()}
        return BytesIO(
            json.dumps(
                {
                    "id": "PAY-1",
                    "result": {"code": "000.000.000"},
                    "merchantTransactionId": "cart-1",
                }
            ).encode("utf-8")
        )

    with patch("providers.hyperpay_adapter.urlopen", side_effect=fake_urlopen):
        payload = adapter.fetch_checkout_result("CHECKOUT-ID-1")

    assert captured["method"] == "GET"
    assert (
        captured["url"]
        == "https://eu-test.oppwa.com/v1/checkouts/CHECKOUT-ID-1/payment?entityId=entity-id-test"
    )
    assert captured["headers"]["authorization"] == "Bearer access-token-test"
    assert payload["id"] == "PAY-1"
