"""Mock PayTabs adapter — no outbound HTTP (dev/CI only)."""

from __future__ import annotations

import json

from domain.events import BillingDomainEvent
from providers.paytabs_adapter import PayTabsAdapter, parse_paytabs_webhook
from providers.port import CheckoutProduct, SubscribeSessionResult

_MOCK_CHECKOUT_URL = "https://mock.paytabs.example/checkout/session"
_MOCK_SIGNATURE = "test"

_PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"
_COURSE_ID = "b0000000-0000-4000-8000-000000000001"
_PLAN_ID = "00000000-0000-4000-8000-000000000001"

MOCK_IPN_SALE_PAID = {
    "tran_ref": "MOCK-ACT-001",
    "tran_type": "Sale",
    "payment_result": "A",
    "cart_id": f"v2|dev|mock-user-sub|course|{_COURSE_ID}|{_PURCHASE_ID}",
    "cart_amount": 99.0,
    "cart_currency": "USD",
    "transaction_time": "2026-05-18T12:00:00Z",
}

# Legacy subscription samples (v1 cart) retained for cancel-agreement IPN tests.
MOCK_IPN_SALE_ACTIVATED = {
    "tran_ref": "MOCK-ACT-001",
    "tran_type": "Sale",
    "payment_result": "A",
    "cart_id": f"v1|dev|mock-user-sub|{_PLAN_ID}",
    "agreement_id": "MOCK-AGR-001",
    "is_recurring": False,
    "transaction_time": "2026-05-18T12:00:00Z",
}

MOCK_IPN_SALE_RENEWED = {
    "tran_ref": "MOCK-REN-001",
    "tran_type": "Sale",
    "payment_result": "A",
    "cart_id": f"v1|dev|mock-user-sub|{_PLAN_ID}",
    "agreement_id": "MOCK-AGR-001",
    "is_recurring": True,
    "recurring_count": 2,
    "transaction_time": "2026-06-18T12:00:00Z",
}

MOCK_IPN_SALE_DECLINED = {
    "tran_ref": "MOCK-DEC-001",
    "tran_type": "Sale",
    "payment_result": "D",
    "cart_id": f"v2|dev|mock-user-sub|bundle|{_PURCHASE_ID}",
    "cart_amount": 150.0,
    "cart_currency": "USD",
}

MOCK_IPN_AGREEMENT_CANCELED = {
    "tran_ref": "MOCK-CAN-001",
    "tran_type": "Agreement",
    "agreement_action": "cancelled",
    "cart_id": f"v1|dev|mock-user-sub|{_PLAN_ID}",
    "agreement_id": "MOCK-AGR-001",
}

MOCK_IPN_REFUND_REVOKED = {
    "tran_ref": "MOCK-REF-001",
    "tran_type": "Refund",
    "payment_result": "A",
    "previous_tran_ref": "MOCK-ACT-001",
    "cart_id": f"v2|dev|mock-user-sub|course|{_COURSE_ID}|{_PURCHASE_ID}",
    "cart_amount": 99.0,
    "cart_currency": "USD",
}


class MockPayTabsAdapter:
    """Fake provider for local runs and CI when PayTabs keys are unavailable."""

    def __init__(self, *, allow_mock_signature: bool = True) -> None:
        self._allow_mock_signature = allow_mock_signature

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
        return SubscribeSessionResult(redirect_url=_MOCK_CHECKOUT_URL)

    def verify_webhook(
        self,
        raw_body: bytes,
        signature_header: str,
        server_key: str = "",
    ) -> bool:
        if server_key:
            return PayTabsAdapter.verify_webhook(raw_body, signature_header, server_key)
        if not self._allow_mock_signature:
            return False
        return signature_header == _MOCK_SIGNATURE

    def parse_webhook(
        self,
        raw_body: bytes,
        *,
        deployment_environment: str,
        payload_digest: str = "",
    ) -> list[BillingDomainEvent]:
        return parse_paytabs_webhook(
            raw_body,
            deployment_environment=deployment_environment,
            payload_digest=payload_digest,
        )

    def cancel_agreement(self, agreement_id: str) -> None:
        _ = agreement_id

    @staticmethod
    def sample_ipn_bytes(sample: dict) -> bytes:
        return json.dumps(sample, separators=(",", ":")).encode("utf-8")
