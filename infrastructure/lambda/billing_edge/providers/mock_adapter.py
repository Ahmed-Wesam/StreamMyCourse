"""Mock PayTabs adapter — no outbound HTTP (dev/CI only)."""

from __future__ import annotations

from typing import Any

from providers.port import SubscribeSessionResult

_MOCK_CHECKOUT_URL = "https://mock.paytabs.example/checkout/session"
_MOCK_SIGNATURE = "test"


class MockPayTabsAdapter:
    """Fake provider for local runs and CI when PayTabs keys are unavailable."""

    def __init__(self, *, allow_mock_signature: bool = True) -> None:
        self._allow_mock_signature = allow_mock_signature

    def create_subscribe_session(
        self,
        *,
        user_sub: str,
        plan_id: str,
        return_url: str | None = None,
    ) -> SubscribeSessionResult:
        _ = user_sub, plan_id, return_url
        return SubscribeSessionResult(redirect_url=_MOCK_CHECKOUT_URL)

    def verify_webhook(
        self,
        raw_body: bytes,
        signature_header: str,
        server_key: str = "",
    ) -> bool:
        _ = raw_body, server_key
        if not self._allow_mock_signature:
            return False
        return signature_header == _MOCK_SIGNATURE

    def parse_webhook(self, raw_body: bytes) -> list[Any]:
        _ = raw_body
        return []

    def cancel_agreement(self, agreement_id: str) -> None:
        _ = agreement_id
        raise NotImplementedError("cancel_agreement is WS7")
