"""Mock PayTabs adapter — no outbound HTTP (dev/CI only)."""

from __future__ import annotations

import json

from domain.events import BillingDomainEvent
from providers.paytabs_adapter import PayTabsAdapter, parse_paytabs_webhook
from providers.port import CheckoutPlan, SubscribeSessionResult

_MOCK_CHECKOUT_URL = "https://mock.paytabs.example/checkout/session"
_MOCK_SIGNATURE = "test"

# Sample IPN bodies for tests and local manual POST (WS3).
MOCK_IPN_SALE_ACTIVATED = {
    "tran_ref": "MOCK-ACT-001",
    "tran_type": "Sale",
    "payment_result": "A",
    "cart_id": "v1|dev|mock-user-sub|00000000-0000-4000-8000-000000000001",
    "agreement_id": "MOCK-AGR-001",
    "is_recurring": False,
    "transaction_time": "2026-05-18T12:00:00Z",
}

MOCK_IPN_SALE_RENEWED = {
    "tran_ref": "MOCK-REN-001",
    "tran_type": "Sale",
    "payment_result": "A",
    "cart_id": "v1|dev|mock-user-sub|00000000-0000-4000-8000-000000000001",
    "agreement_id": "MOCK-AGR-001",
    "is_recurring": True,
    "recurring_count": 2,
    "transaction_time": "2026-06-18T12:00:00Z",
}

MOCK_IPN_SALE_DECLINED = {
    "tran_ref": "MOCK-DEC-001",
    "tran_type": "Sale",
    "payment_result": "D",
    "cart_id": "v1|dev|mock-user-sub|00000000-0000-4000-8000-000000000001",
    "agreement_id": "MOCK-AGR-001",
}

MOCK_IPN_AGREEMENT_CANCELED = {
    "tran_ref": "MOCK-CAN-001",
    "tran_type": "Agreement",
    "agreement_action": "cancelled",
    "cart_id": "v1|dev|mock-user-sub|00000000-0000-4000-8000-000000000001",
    "agreement_id": "MOCK-AGR-001",
}

MOCK_IPN_REFUND_IGNORED = {
    "tran_ref": "MOCK-REF-001",
    "tran_type": "Refund",
    "payment_result": "A",
    "cart_id": "v1|dev|mock-user-sub|00000000-0000-4000-8000-000000000001",
}


class MockPayTabsAdapter:
    """Fake provider for local runs and CI when PayTabs keys are unavailable."""

    def __init__(self, *, allow_mock_signature: bool = True) -> None:
        self._allow_mock_signature = allow_mock_signature

    def create_subscribe_session(
        self,
        *,
        user_sub: str,
        plan_id: str,
        plan: CheckoutPlan | None = None,
        return_url: str | None = None,
    ) -> SubscribeSessionResult:
        _ = user_sub, plan_id, plan, return_url
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

    def resume_agreement(self, agreement_id: str) -> None:
        _ = agreement_id

    @staticmethod
    def sample_ipn_bytes(sample: dict) -> bytes:
        return json.dumps(sample, separators=(",", ":")).encode("utf-8")
