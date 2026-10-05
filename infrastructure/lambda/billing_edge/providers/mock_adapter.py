"""Mock HyperPay adapter — no outbound HTTP (dev/CI only)."""

from __future__ import annotations

import json
from typing import Any

from domain.events import BillingDomainEvent
from providers.hyperpay_adapter import HyperPayAdapter, parse_hyperpay_webhook
from domain.checkout_billing import CheckoutBillingContact
from providers.port import CheckoutProduct, HyperPayCheckoutResult, SubscribeSessionResult

_MOCK_HYPERPAY_WIDGET_URL = (
    "https://mock.hyperpay.example/v1/paymentWidgets.js?checkoutId=MOCK-HP-CHECKOUT"
)

_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"
_USER_SUB = "student-sub-1"
_CART_V2 = f"v2|dev|{_USER_SUB}|course|{_COURSE_ID}|{_PURCHASE_ID}"


class MockHyperPayAdapter:
    """Fake HyperPay provider for local runs and CI."""

    def create_checkout(
        self,
        *,
        user_sub: str,
        purchase_id: str,
        product_type: str,
        course_id: str | None,
        product: CheckoutProduct,
        customer_email: str,
        billing: CheckoutBillingContact,
    ) -> HyperPayCheckoutResult:
        _ = user_sub, purchase_id, product_type, course_id, product, customer_email, billing
        return HyperPayCheckoutResult(
            checkout_id="MOCK-HP-CHECKOUT",
            widget_url=_MOCK_HYPERPAY_WIDGET_URL,
            integrity="sha384-mock",
        )

    def fetch_checkout_result(self, checkout_id: str) -> dict[str, Any]:
        _ = checkout_id
        return {
            "id": "MOCK-PAYMENT",
            "merchantTransactionId": _CART_V2,
            "amount": "50.000",
            "currency": "JOD",
            "result": {"code": "000.200.000", "description": "Pending"},
        }

    @staticmethod
    def decrypt_webhook(
        *,
        ciphertext_hex: bytes | str,
        iv_hex: str,
        auth_tag_hex: str,
        webhook_secret_hex: str,
    ) -> bytes:
        return HyperPayAdapter.decrypt_webhook(
            ciphertext_hex=ciphertext_hex,
            iv_hex=iv_hex,
            auth_tag_hex=auth_tag_hex,
            webhook_secret_hex=webhook_secret_hex,
        )

    def parse_webhook(
        self,
        raw_body: bytes,
        *,
        deployment_environment: str,
        payload_digest: str = "",
    ) -> list[BillingDomainEvent]:
        return parse_hyperpay_webhook(
            raw_body,
            deployment_environment=deployment_environment,
            payload_digest=payload_digest,
        )

    def create_sale_session(
        self,
        *,
        user_sub: str,
        purchase_id: str,
        product_type: str,
        course_id: str | None,
        product: CheckoutProduct,
    ) -> SubscribeSessionResult:
        _ = user_sub, purchase_id, product_type, course_id, product
        raise NotImplementedError()

    def verify_webhook(
        self,
        raw_body: bytes,
        signature_header: str,
        server_key: str = "",
    ) -> bool:
        _ = raw_body, signature_header, server_key
        return False

    def cancel_agreement(self, agreement_id: str) -> None:
        _ = agreement_id

    @staticmethod
    def sample_notification_bytes(sample: dict) -> bytes:
        return json.dumps(sample, separators=(",", ":")).encode("utf-8")
