"""PayTabs payment provider adapter (WS2: verify_webhook; HPP stub until WS6)."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from providers.port import SubscribeSessionResult


class BillingUnconfiguredError(Exception):
    """Raised when PayTabs credentials are missing for a configured route."""


class PayTabsAdapter:
    """Live PayTabs integration — no outbound HTTP in WS2 unit tests."""

    def __init__(
        self,
        *,
        server_key: str,
        profile_id: str,
        api_domain: str,
    ) -> None:
        self._server_key = server_key.strip()
        self._profile_id = profile_id.strip()
        self._api_domain = api_domain.strip()

    @property
    def server_key(self) -> str:
        return self._server_key

    def _has_keys(self) -> bool:
        return bool(self._server_key and self._profile_id)

    def create_subscribe_session(
        self,
        *,
        user_sub: str,
        plan_id: str,
        return_url: str | None = None,
    ) -> SubscribeSessionResult:
        _ = user_sub, plan_id, return_url
        if not self._has_keys():
            raise BillingUnconfiguredError()
        raise NotImplementedError("PayTabs HPP payment/request is WS6")

    @staticmethod
    def verify_webhook(
        raw_body: bytes,
        signature_header: str,
        server_key: str,
    ) -> bool:
        """HMAC-SHA256(raw body, Server Key) per PayTabs IPN docs."""
        if not server_key or not signature_header:
            return False
        expected = hmac.new(
            server_key.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        received = signature_header.strip().lower()
        return hmac.compare_digest(expected, received)

    def parse_webhook(self, raw_body: bytes) -> list[Any]:
        _ = raw_body
        return []

    def cancel_agreement(self, agreement_id: str) -> None:
        _ = agreement_id
        raise NotImplementedError("cancel_agreement is WS7")
