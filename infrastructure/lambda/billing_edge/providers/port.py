"""Payment provider port (WS2 + RS-5 one-time sale)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from domain.checkout_billing import CheckoutBillingContact


@dataclass(frozen=True)
class SubscribeSessionResult:
    redirect_url: str


@dataclass(frozen=True)
class HyperPayCheckoutResult:
    checkout_id: str
    widget_url: str
    integrity: str | None = None


@dataclass(frozen=True)
class CheckoutPlan:
    amount_minor: int
    currency: str
    plan_key: str


@dataclass(frozen=True)
class CheckoutProduct:
    amount_minor: int
    currency: str
    description: str


@runtime_checkable
class PaymentProviderPort(Protocol):
    def create_sale_session(
        self,
        *,
        user_sub: str,
        purchase_id: str,
        product_type: str,
        course_id: str | None,
        product: CheckoutProduct,
    ) -> SubscribeSessionResult:
        """Start HPP one-time sale; returns redirect URL for the student SPA."""

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
        """Start HyperPay COPYandPAY checkout (JOD one-time purchase)."""

    def fetch_checkout_result(self, checkout_id: str) -> dict[str, Any]:
        """Poll HyperPay checkout payment status after shopper return."""

    def decrypt_webhook(
        self,
        *,
        ciphertext_hex: bytes | str,
        iv_hex: str,
        auth_tag_hex: str,
        webhook_secret_hex: str,
    ) -> bytes:
        """Decrypt AES-256-GCM HyperPay webhook body (IV/tag in HTTP headers)."""

