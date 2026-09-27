"""PayTabs payment provider adapter (WS2: verify_webhook; WS3: parse_webhook; RS-5: sale)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from domain.events import BillingDomainEvent
from domain.metadata import (
    EnvironmentMismatchError,
    InvalidCartMetadataError,
    MissingSubscriptionPeriodError,
    parse_cart_metadata,
)
from domain.period_bounds import ensure_grant_period_bounds
from providers.port import CheckoutProduct, SubscribeSessionResult

_PROVIDER = "paytabs"
logger = logging.getLogger(__name__)

# IPN types we acknowledge with 200 but do not enqueue (WS3 ignore-list).
IGNORED_TRAN_TYPES = frozenset(
    {
        "Auth",
        "Capture",
        "Void",
        "Register",
        "Inquiry",
    }
)

_SUPPORTED_SALE_PAYMENT_RESULTS = frozenset({"A", "D", "E"})
_AGREEMENT_CANCEL_ACTIONS = frozenset({"cancelled", "canceled", "cancel"})


class BillingUnconfiguredError(Exception):
    """Raised when PayTabs credentials are missing for a configured route."""


class InvalidRedirectUrlError(Exception):
    """PayTabs returned a redirect URL outside the allowed host set."""


def _payment_result_code(payload: dict[str, Any]) -> str:
    raw = payload.get("payment_result")
    if isinstance(raw, dict):
        status = raw.get("response_status") or raw.get("responseStatus")
        if status is not None:
            return str(status).strip().upper()
    if raw is not None and not isinstance(raw, dict):
        return str(raw).strip().upper()
    return ""


def _cart_amount_minor(payload: dict[str, Any]) -> int | None:
    amount = payload.get("cart_amount")
    currency = str(payload.get("cart_currency") or "").strip().upper()
    if amount is None or currency != "USD":
        return None
    try:
        return int(round(float(amount) * 100))
    except (TypeError, ValueError):
        return None


def _provider_event_id(tran_ref: str, payment_result: str) -> str:
    return f"paytabs:{tran_ref}:{payment_result}"


def _agreement_provider_event_id(agreement_id: str, event_kind: str) -> str:
    return f"paytabs:{agreement_id}:{event_kind}"


def _is_recurring_sale(payload: dict[str, Any]) -> bool:
    if payload.get("is_recurring") is True:
        return True
    recurring_count = payload.get("recurring_count")
    if isinstance(recurring_count, int) and recurring_count >= 1:
        return True
    if isinstance(recurring_count, str) and recurring_count.isdigit() and int(recurring_count) >= 1:
        return True
    recurring_index = payload.get("recurring_index")
    if isinstance(recurring_index, int) and recurring_index >= 1:
        return True
    if isinstance(recurring_index, str) and recurring_index.isdigit() and int(recurring_index) >= 1:
        return True
    return False


def _period_bounds(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    start = payload.get("subscription_period_start") or payload.get("period_start")
    end = payload.get("subscription_period_end") or payload.get("period_end")
    if start is not None:
        start = str(start)
    if end is not None:
        end = str(end)
    return start, end


def _purchase_domain_event(
    *,
    event_type: str,
    metadata: Any,
    provider_event_id: str,
    payload_digest: str,
    provider_tran_ref: str | None,
    amount_minor: int | None,
    currency: str | None,
) -> BillingDomainEvent:
    return BillingDomainEvent(
        event_type=event_type,
        provider=_PROVIDER,
        provider_event_id=provider_event_id,
        environment=metadata.environment,
        user_sub=metadata.user_sub,
        plan_id="",
        payload_digest=payload_digest,
        purchase_id=metadata.purchase_id,
        product_type=metadata.product_type,
        course_id=metadata.course_id,
        amount_minor=amount_minor,
        currency=currency,
        provider_tran_ref=provider_tran_ref,
    )


def _parse_purchase_sale(
    payload: dict[str, Any],
    *,
    metadata: Any,
    payload_digest: str,
) -> list[BillingDomainEvent]:
    if _is_recurring_sale(payload):
        return []

    tran_ref = str(payload.get("tran_ref") or "").strip()
    if not tran_ref:
        raise InvalidCartMetadataError("tran_ref is required for Sale IPN")

    payment_result = _payment_result_code(payload)
    if not payment_result:
        raise InvalidCartMetadataError("payment_result is required for Sale IPN")

    provider_event_id = _provider_event_id(tran_ref, payment_result)
    amount_minor = _cart_amount_minor(payload)
    currency = str(payload.get("cart_currency") or "").strip().upper() or None

    if payment_result == "A":
        return [
            _purchase_domain_event(
                event_type="purchase.paid",
                metadata=metadata,
                provider_event_id=provider_event_id,
                payload_digest=payload_digest,
                provider_tran_ref=tran_ref,
                amount_minor=amount_minor,
                currency=currency,
            )
        ]

    if payment_result in ("D", "E"):
        return [
            _purchase_domain_event(
                event_type="purchase.failed",
                metadata=metadata,
                provider_event_id=provider_event_id,
                payload_digest=payload_digest,
                provider_tran_ref=tran_ref,
                amount_minor=amount_minor,
                currency=currency,
            )
        ]

    expected = ", ".join(sorted(_SUPPORTED_SALE_PAYMENT_RESULTS))
    raise InvalidCartMetadataError(
        f"unsupported payment_result {payment_result!r} for Sale IPN (expected {expected})"
    )


def _parse_subscription_sale(
    payload: dict[str, Any],
    *,
    metadata: Any,
    payload_digest: str,
    agreement_id: str | None,
) -> list[BillingDomainEvent]:
    tran_ref = str(payload.get("tran_ref") or "").strip()
    if not tran_ref:
        raise InvalidCartMetadataError("tran_ref is required for Sale IPN")

    payment_result = _payment_result_code(payload)
    if not payment_result:
        raise InvalidCartMetadataError("payment_result is required for Sale IPN")

    provider_event_id = _provider_event_id(tran_ref, payment_result)
    period_start, period_end = _period_bounds(payload)

    if payment_result == "A":
        event_type = (
            "subscription.renewed" if _is_recurring_sale(payload) else "subscription.activated"
        )
        period_start, period_end = ensure_grant_period_bounds(payload, period_start, period_end)
        if not period_end:
            raise MissingSubscriptionPeriodError(
                "authorized Sale IPN must include period_end or transaction_time"
            )
        return [
            BillingDomainEvent(
                event_type=event_type,
                provider=_PROVIDER,
                provider_event_id=provider_event_id,
                environment=metadata.environment,
                user_sub=metadata.user_sub,
                plan_id=metadata.plan_id,
                payload_digest=payload_digest,
                provider_subscription_id=agreement_id,
                current_period_start=period_start,
                current_period_end=period_end,
            )
        ]

    if payment_result in ("D", "E"):
        fail_start, fail_end = ensure_grant_period_bounds(payload, period_start, period_end)
        return [
            BillingDomainEvent(
                event_type="subscription.payment_failed",
                provider=_PROVIDER,
                provider_event_id=provider_event_id,
                environment=metadata.environment,
                user_sub=metadata.user_sub,
                plan_id=metadata.plan_id,
                payload_digest=payload_digest,
                provider_subscription_id=agreement_id,
                current_period_start=fail_start,
                current_period_end=fail_end,
            )
        ]

    expected = ", ".join(sorted(_SUPPORTED_SALE_PAYMENT_RESULTS))
    raise InvalidCartMetadataError(
        f"unsupported payment_result {payment_result!r} for Sale IPN (expected {expected})"
    )


def parse_paytabs_webhook(
    raw_body: bytes,
    *,
    deployment_environment: str,
    payload_digest: str = "",
) -> list[BillingDomainEvent]:
    """Map PayTabs IPN JSON to neutral domain events."""
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []

    if not isinstance(payload, dict):
        return []

    tran_type = str(payload.get("tran_type") or "").strip()
    if tran_type in IGNORED_TRAN_TYPES:
        return []

    cart_id = str(payload.get("cart_id") or "").strip()
    requires_cart = tran_type in ("Sale", "Agreement", "Refund")
    if requires_cart and not cart_id:
        raise InvalidCartMetadataError("cart_id is required for subscription IPN")

    if not cart_id and tran_type != "Refund":
        return []

    metadata = None
    if cart_id:
        try:
            metadata = parse_cart_metadata(cart_id, deployment_environment)
        except EnvironmentMismatchError:
            raise
        except ValueError as exc:
            raise InvalidCartMetadataError(str(exc)) from exc

    agreement_id = str(payload.get("agreement_id") or "").strip() or None
    period_start, period_end = _period_bounds(payload)

    if tran_type == "Refund":
        if metadata is None or not metadata.is_purchase:
            return []
        previous_tran_ref = str(payload.get("previous_tran_ref") or "").strip()
        tran_ref = str(payload.get("tran_ref") or "").strip()
        if not previous_tran_ref:
            raise InvalidCartMetadataError("previous_tran_ref is required for Refund IPN")
        refund_event_id = _provider_event_id(tran_ref or previous_tran_ref, "R")
        return [
            _purchase_domain_event(
                event_type="purchase.revoked",
                metadata=metadata,
                provider_event_id=refund_event_id,
                payload_digest=payload_digest,
                provider_tran_ref=previous_tran_ref,
                amount_minor=_cart_amount_minor(payload),
                currency=str(payload.get("cart_currency") or "").strip().upper() or None,
            )
        ]

    if tran_type == "Agreement":
        if metadata is None or not metadata.plan_id:
            raise InvalidCartMetadataError("cart_id is required for Agreement cancel IPN")
        action = str(
            payload.get("agreement_action")
            or payload.get("agreement_status")
            or payload.get("payment_result")
            or ""
        ).strip().lower()
        if action not in _AGREEMENT_CANCEL_ACTIONS:
            raise InvalidCartMetadataError(
                f"unsupported Agreement action {action!r}; expected cancel"
            )
        if not agreement_id:
            raise InvalidCartMetadataError(
                "agreement_id is required for Agreement cancel IPN"
            )
        canceled_at = payload.get("canceled_at") or payload.get("transaction_time")
        return [
            BillingDomainEvent(
                event_type="subscription.canceled",
                provider=_PROVIDER,
                provider_event_id=_agreement_provider_event_id(agreement_id, "canceled"),
                environment=metadata.environment,
                user_sub=metadata.user_sub,
                plan_id=metadata.plan_id,
                payload_digest=payload_digest,
                provider_subscription_id=agreement_id,
                cancel_at_period_end=False,
                canceled_at=str(canceled_at) if canceled_at is not None else None,
            )
        ]

    if tran_type != "Sale":
        raise InvalidCartMetadataError(
            f"unsupported tran_type {tran_type!r} for subscription IPN (expected Sale or Agreement)"
        )

    assert metadata is not None
    if metadata.is_purchase:
        return _parse_purchase_sale(payload, metadata=metadata, payload_digest=payload_digest)

    return _parse_subscription_sale(
        payload,
        metadata=metadata,
        payload_digest=payload_digest,
        agreement_id=agreement_id,
    )


_CENTS_PER_USD = 100


def _amount_minor_to_cart_amount_usd(amount_minor: int) -> float:
    return round(amount_minor / _CENTS_PER_USD, 2)


def _build_purchase_cart_id(
    *,
    deployment_environment: str,
    user_sub: str,
    product_type: str,
    course_id: str | None,
    purchase_id: str,
) -> str:
    env = deployment_environment.strip().lower()
    if product_type == "course":
        if not course_id:
            raise ValueError("course_id is required for course sale cart_id")
        return f"v2|{env}|{user_sub}|course|{course_id}|{purchase_id}"
    return f"v2|{env}|{user_sub}|bundle|{purchase_id}"


def _validate_redirect_host(redirect_url: str, api_domain: str) -> None:
    parsed = urlparse(redirect_url)
    host = (parsed.hostname or "").lower()
    allowed = {api_domain.strip().lower(), "mock.paytabs.example"}
    if host not in allowed:
        raise InvalidRedirectUrlError(f"redirect host {host!r} is not allowed")


class PayTabsAdapter:
    """Live PayTabs integration — outbound HTTP in create_sale_session and cancel_agreement."""

    def __init__(
        self,
        *,
        server_key: str,
        profile_id: str,
        api_domain: str,
        deployment_environment: str,
        return_success_url: str | None = None,
        ipn_callback_url: str | None = None,
        return_cancel_url: str | None = None,
    ) -> None:
        self._server_key = server_key.strip()
        self._profile_id = profile_id.strip()
        self._api_domain = api_domain.strip().rstrip("/")
        self._deployment_environment = deployment_environment.strip().lower()
        self._return_success_url = (return_success_url or "").strip()
        self._ipn_callback_url = (ipn_callback_url or "").strip()
        self._return_cancel_url = (return_cancel_url or "").strip()

    @property
    def server_key(self) -> str:
        return self._server_key

    def _has_keys(self) -> bool:
        return bool(self._server_key and self._profile_id)

    def create_sale_session(
        self,
        *,
        user_sub: str,
        purchase_id: str,
        product_type: str,
        course_id: str | None,
        product: CheckoutProduct,
    ) -> SubscribeSessionResult:
        if not self._has_keys():
            raise BillingUnconfiguredError()
        if not self._return_success_url or not self._ipn_callback_url:
            raise BillingUnconfiguredError()

        normalized_type = (product_type or "").strip().lower()
        if normalized_type not in ("course", "bundle"):
            raise BillingUnconfiguredError()

        cart_id = _build_purchase_cart_id(
            deployment_environment=self._deployment_environment,
            user_sub=user_sub,
            product_type=normalized_type,
            course_id=course_id,
            purchase_id=purchase_id,
        )
        request_body = {
            "profile_id": int(self._profile_id)
            if self._profile_id.isdigit()
            else self._profile_id,
            "tran_type": "sale",
            "tran_class": "ecom",
            "cart_id": cart_id,
            "cart_description": product.description,
            "cart_currency": "USD",
            "cart_amount": _amount_minor_to_cart_amount_usd(product.amount_minor),
            "return": self._return_success_url,
            "callback": self._ipn_callback_url,
        }
        encoded = json.dumps(request_body, separators=(",", ":")).encode("utf-8")
        url = f"https://{self._api_domain}/payment/request"
        req = Request(
            url,
            data=encoded,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "authorization": self._server_key,
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                raw = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise BillingUnconfiguredError() from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BillingUnconfiguredError() from exc

        if not isinstance(payload, dict):
            raise BillingUnconfiguredError()

        redirect = str(payload.get("redirect_url") or "").strip()
        if not redirect:
            raise BillingUnconfiguredError()

        try:
            _validate_redirect_host(redirect, self._api_domain)
        except InvalidRedirectUrlError as exc:
            raise BillingUnconfiguredError() from exc

        return SubscribeSessionResult(redirect_url=redirect)

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
        if not self._has_keys():
            raise BillingUnconfiguredError()

        request_body = {
            "profile_id": int(self._profile_id)
            if self._profile_id.isdigit()
            else self._profile_id,
            "agreement_id": agreement_id.strip(),
        }
        encoded = json.dumps(request_body, separators=(",", ":")).encode("utf-8")
        url = f"https://{self._api_domain}/payment/agreement/cancel"
        req = Request(
            url,
            data=encoded,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "authorization": self._server_key,
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise BillingUnconfiguredError() from exc
