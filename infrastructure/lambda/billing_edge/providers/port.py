"""Payment provider port (WS2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SubscribeSessionResult:
    redirect_url: str


@dataclass(frozen=True)
class CheckoutPlan:
    amount_minor: int
    currency: str
    plan_key: str


@runtime_checkable
class PaymentProviderPort(Protocol):
    def create_subscribe_session(
        self,
        *,
        user_sub: str,
        plan_id: str,
        plan: CheckoutPlan | None = None,
        return_url: str | None = None,
    ) -> SubscribeSessionResult:
        """Start HPP subscribe flow; returns redirect URL for the student SPA."""

    def verify_webhook(
        self,
        raw_body: bytes,
        signature_header: str,
        server_key: str = "",
    ) -> bool:
        """Validate IPN / callback signature."""

    def parse_webhook(
        self,
        raw_body: bytes,
        *,
        deployment_environment: str,
        payload_digest: str = "",
    ) -> list[Any]:
        """Map provider payload to neutral domain events (WS3)."""

    def cancel_agreement(self, agreement_id: str) -> None:
        """Cancel Repeat Billing agreement (WS7 mock no-op; live deferred to WS8)."""
