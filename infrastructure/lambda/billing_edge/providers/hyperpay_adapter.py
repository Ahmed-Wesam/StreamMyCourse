"""HyperPay payment provider adapter (checkout, webhook decrypt/parse)."""

from __future__ import annotations

import json
import logging
from typing import Any, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from domain.amounts import fils_to_hyperpay_amount, validate_whole_jod_fils
from domain.checkout_billing import CheckoutBillingContact
from domain.events import BillingDomainEvent
from domain.metadata import (
    EnvironmentMismatchError,
    InvalidCartMetadataError,
    parse_cart_metadata,
)
from domain.result_codes import classify_result_code
from providers.port import CheckoutProduct, HyperPayCheckoutResult

_PROVIDER = "hyperpay"
logger = logging.getLogger(__name__)

_TEST_API_HOST = "eu-test.oppwa.com"
_PROD_API_HOST = "eu-prod.oppwa.com"

# HyperPay may return these when GET /payment is early, expired, or temporarily unavailable.
_POLL_TREAT_AS_PENDING_CODES = frozenset(
    {
        "200.300.404",
        "800.120.100",
    }
)
_POLL_TREAT_AS_PENDING_PREFIXES = ("800.120.",)
_MOCK_API_HOST = "mock.hyperpay.example"
_ALLOWED_API_HOSTS = frozenset({_TEST_API_HOST, _PROD_API_HOST, _MOCK_API_HOST})

_IGNORED_NOTIFICATION_TYPES = frozenset({"REGISTRATION", "SCHEDULE", "RISK"})


class BillingUnconfiguredError(Exception):
    """Raised when HyperPay credentials or routes are missing."""


class InvalidWidgetHostError(Exception):
    """Widget base host is outside the allowed OPPWA set."""


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


def _normalize_api_host(api_host: str) -> str:
    return api_host.strip().lower().rstrip("/")


def _validate_api_host(api_host: str) -> str:
    normalized = _normalize_api_host(api_host)
    if normalized not in _ALLOWED_API_HOSTS:
        raise InvalidWidgetHostError(f"api host {normalized!r} is not allowed")
    return normalized


def _widget_url(api_host: str, checkout_id: str) -> str:
    host = _validate_api_host(api_host)
    checkout = checkout_id.strip()
    if not checkout:
        raise BillingUnconfiguredError()
    return f"https://{host}/v1/paymentWidgets.js?checkoutId={checkout}"


def _jod_amount_minor(payload: dict[str, Any]) -> int | None:
    amount = payload.get("amount")
    currency = str(payload.get("currency") or "").strip().upper()
    if amount is None or currency != "JOD":
        return None
    try:
        major = float(amount)
        return int(round(major * 1000))
    except (TypeError, ValueError):
        return None


def _provider_event_id(payment_id: str, result_code: str) -> str:
    return f"hyperpay:{payment_id}:{result_code}"


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


def _custom_parameter_cart_id(payload: dict[str, Any]) -> str:
    custom = payload.get("customParameters")
    if not isinstance(custom, dict):
        return ""
    for key in ("SHOPPER_cart", "SHOPPER_CART"):
        val = str(custom.get(key) or "").strip()
        if val:
            return val
    return ""


def _extract_merchant_transaction_id(payload: dict[str, Any]) -> str:
    merchant_tx = str(payload.get("merchantTransactionId") or "").strip()
    if merchant_tx:
        return merchant_tx
    payment_block = payload.get("payment")
    if isinstance(payment_block, dict):
        merchant_tx = str(payment_block.get("merchantTransactionId") or "").strip()
        if merchant_tx:
            return merchant_tx
        merchant_tx = _custom_parameter_cart_id(payment_block)
        if merchant_tx:
            return merchant_tx
    return _custom_parameter_cart_id(payload)


def _poll_result_code(payload: dict[str, Any]) -> str:
    result = payload.get("result")
    if isinstance(result, dict):
        code = str(result.get("code") or "").strip()
        if code:
            return code
    payment_block = payload.get("payment")
    if isinstance(payment_block, dict):
        nested = payment_block.get("result")
        if isinstance(nested, dict):
            return str(nested.get("code") or "").strip()
    return ""


def parse_checkout_payment_poll(
    payload: dict[str, Any],
    *,
    deployment_environment: str,
    payload_digest: str = "",
) -> tuple[str, list[BillingDomainEvent]]:
    """Map GET checkout/payment JSON to pending|success|failed and domain events."""
    result_code = _poll_result_code(payload)
    payment_block = payload.get("payment")
    if not result_code and isinstance(payment_block, dict):
        nested = payment_block.get("result")
        if isinstance(nested, dict):
            result_code = str(nested.get("code") or "").strip()

    merchant_tx = _extract_merchant_transaction_id(payload)

    if not result_code:
        raise InvalidCartMetadataError("result.code is required for checkout payment poll")

    if result_code in _POLL_TREAT_AS_PENDING_CODES or result_code.startswith(
        _POLL_TREAT_AS_PENDING_PREFIXES
    ):
        return "pending", []

    classification = classify_result_code(result_code)
    if classification == "pending":
        return "pending", []

    if not merchant_tx:
        if classification == "failed":
            return "failed", []
        raise InvalidCartMetadataError(
            "merchantTransactionId is required for checkout payment poll"
        )

    try:
        metadata = parse_cart_metadata(merchant_tx, deployment_environment)
    except EnvironmentMismatchError:
        raise
    except ValueError as exc:
        raise InvalidCartMetadataError(str(exc)) from exc

    if not metadata.is_purchase:
        return classification, []

    payment_id = str(payload.get("id") or "").strip()
    if not payment_id:
        payment_block = payload.get("payment")
        if isinstance(payment_block, dict):
            payment_id = str(payment_block.get("id") or "").strip()
    if not payment_id:
        raise InvalidCartMetadataError("payment id is required for checkout payment poll")

    amount_minor = _jod_amount_minor(payload)
    currency = str(payload.get("currency") or "").strip().upper() or None
    if amount_minor is None:
        payment_block = payload.get("payment")
        if isinstance(payment_block, dict):
            amount_minor = _jod_amount_minor(payment_block)
            if currency is None:
                currency = str(payment_block.get("currency") or "").strip().upper() or None

    provider_event_id = _provider_event_id(payment_id, result_code)

    if classification == "success":
        return "success", [
            _purchase_domain_event(
                event_type="purchase.paid",
                metadata=metadata,
                provider_event_id=provider_event_id,
                payload_digest=payload_digest,
                provider_tran_ref=payment_id,
                amount_minor=amount_minor,
                currency=currency,
            )
        ]

    return "failed", [
        _purchase_domain_event(
            event_type="purchase.failed",
            metadata=metadata,
            provider_event_id=provider_event_id,
            payload_digest=payload_digest,
            provider_tran_ref=payment_id,
            amount_minor=amount_minor,
            currency=currency,
        )
    ]


def parse_hyperpay_webhook(
    raw_body: bytes,
    *,
    deployment_environment: str,
    payload_digest: str = "",
) -> list[BillingDomainEvent]:
    """Map decrypted HyperPay webhook JSON to neutral domain events."""
    try:
        envelope = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []

    if not isinstance(envelope, dict):
        return []

    notification_type = str(envelope.get("type") or "").strip().upper()
    if notification_type in _IGNORED_NOTIFICATION_TYPES:
        return []

    if notification_type != "PAYMENT":
        return []

    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return []

    payment_type = str(payload.get("paymentType") or "").strip().upper()
    if payment_type not in ("DB", "RF"):
        return []

    payment_id = str(payload.get("id") or "").strip()
    if not payment_id:
        raise InvalidCartMetadataError("payment id is required for HyperPay PAYMENT notification")

    merchant_tx = str(payload.get("merchantTransactionId") or "").strip()
    if not merchant_tx:
        raise InvalidCartMetadataError(
            "merchantTransactionId is required for HyperPay PAYMENT notification"
        )

    try:
        metadata = parse_cart_metadata(merchant_tx, deployment_environment)
    except EnvironmentMismatchError:
        raise
    except ValueError as exc:
        raise InvalidCartMetadataError(str(exc)) from exc

    if not metadata.is_purchase:
        return []

    result = payload.get("result")
    result_code = ""
    if isinstance(result, dict):
        result_code = str(result.get("code") or "").strip()
    if not result_code:
        raise InvalidCartMetadataError("result.code is required for HyperPay PAYMENT notification")

    amount_minor = _jod_amount_minor(payload)
    currency = str(payload.get("currency") or "").strip().upper() or None
    provider_event_id = _provider_event_id(payment_id, result_code)

    if payment_type == "RF":
        referenced = str(payload.get("referencedId") or "").strip() or payment_id
        return [
            _purchase_domain_event(
                event_type="purchase.revoked",
                metadata=metadata,
                provider_event_id=provider_event_id,
                payload_digest=payload_digest,
                provider_tran_ref=referenced,
                amount_minor=amount_minor,
                currency=currency,
            )
        ]

    classification = classify_result_code(result_code)
    if classification == "pending":
        return []

    if classification == "success":
        return [
            _purchase_domain_event(
                event_type="purchase.paid",
                metadata=metadata,
                provider_event_id=provider_event_id,
                payload_digest=payload_digest,
                provider_tran_ref=payment_id,
                amount_minor=amount_minor,
                currency=currency,
            )
        ]

    return [
        _purchase_domain_event(
            event_type="purchase.failed",
            metadata=metadata,
            provider_event_id=provider_event_id,
            payload_digest=payload_digest,
            provider_tran_ref=payment_id,
            amount_minor=amount_minor,
            currency=currency,
        )
    ]


class HyperPayAdapter:
    """Live HyperPay integration — outbound HTTP via stdlib urllib."""

    def __init__(
        self,
        *,
        access_token: str,
        entity_id: str,
        api_host: str,
        deployment_environment: str,
        shopper_result_url: str | None = None,
    ) -> None:
        self._access_token = access_token.strip()
        self._entity_id = entity_id.strip()
        self._api_host = _normalize_api_host(api_host)
        self._deployment_environment = deployment_environment.strip().lower()
        self._shopper_result_url = (shopper_result_url or "").strip()

    def _has_credentials(self) -> bool:
        return bool(self._access_token and self._entity_id)

    def _auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

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
        if not self._has_credentials() or not self._shopper_result_url:
            raise BillingUnconfiguredError()

        try:
            _validate_api_host(self._api_host)
        except InvalidWidgetHostError as exc:
            raise BillingUnconfiguredError() from exc

        normalized_type = (product_type or "").strip().lower()
        if normalized_type not in ("course", "bundle"):
            raise BillingUnconfiguredError()

        validate_whole_jod_fils(product.amount_minor)

        cart_id = _build_purchase_cart_id(
            deployment_environment=self._deployment_environment,
            user_sub=user_sub,
            product_type=normalized_type,
            course_id=course_id,
            purchase_id=purchase_id,
        )

        email = (customer_email or "").strip()
        if not email:
            raise BillingUnconfiguredError()

        form_fields: list[tuple[str, str]] = [
            ("entityId", self._entity_id),
            ("amount", fils_to_hyperpay_amount(product.amount_minor)),
            ("currency", "JOD"),
            ("paymentType", "DB"),
            ("integrity", "true"),
            ("merchantTransactionId", cart_id),
            ("shopperResultUrl", self._shopper_result_url),
            ("customer.email", email),
            ("customer.givenName", billing.given_name),
            ("customer.surname", billing.surname),
            ("billing.street1", billing.street),
            ("billing.city", billing.city),
            ("billing.state", billing.state),
            ("billing.country", billing.country),
            ("billing.postcode", billing.postcode),
            ("customParameters[SHOPPER_cart]", cart_id),
        ]
        if self._api_host == _TEST_API_HOST:
            form_fields.append(("testMode", "EXTERNAL"))
            form_fields.append(("customParameters[3DS2_enrolled]", "true"))

        encoded_body = urlencode(form_fields).encode("utf-8")
        url = f"https://{self._api_host}/v1/checkouts"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            **self._auth_header(),
        }
        req = Request(url, data=encoded_body, method="POST", headers=headers)
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

        checkout_id = str(payload.get("id") or "").strip()
        if not checkout_id:
            raise BillingUnconfiguredError()

        integrity = str(payload.get("integrity") or "").strip() or None
        try:
            widget_url = _widget_url(self._api_host, checkout_id)
        except (InvalidWidgetHostError, BillingUnconfiguredError) as exc:
            raise BillingUnconfiguredError() from exc

        return HyperPayCheckoutResult(
            checkout_id=checkout_id,
            widget_url=widget_url,
            integrity=integrity,
        )

    def fetch_checkout_result(self, checkout_id: str) -> dict[str, Any]:
        if not self._has_credentials():
            raise BillingUnconfiguredError()

        checkout = checkout_id.strip()
        if not checkout:
            raise BillingUnconfiguredError()

        query = urlencode({"entityId": self._entity_id})
        url = f"https://{self._api_host}/v1/checkouts/{checkout}/payment?{query}"
        req = Request(url, method="GET", headers=self._auth_header())
        try:
            with urlopen(req, timeout=30) as response:
                raw = response.read()
        except HTTPError as exc:
            raw = exc.read()
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as parse_exc:
                raise BillingUnconfiguredError() from exc
            if isinstance(payload, dict) and _poll_result_code(payload):
                return payload
            raise BillingUnconfiguredError() from exc
        except (URLError, TimeoutError) as exc:
            raise BillingUnconfiguredError() from exc

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise BillingUnconfiguredError() from exc

        if not isinstance(payload, dict):
            raise BillingUnconfiguredError()
        return payload

    @staticmethod
    def decrypt_webhook(
        *,
        ciphertext_hex: bytes | str,
        iv_hex: str,
        auth_tag_hex: str,
        webhook_secret_hex: str,
    ) -> bytes:
        key = bytes.fromhex((webhook_secret_hex or "").strip())
        iv = bytes.fromhex((iv_hex or "").strip())
        tag = bytes.fromhex((auth_tag_hex or "").strip())
        if isinstance(ciphertext_hex, bytes):
            cipher_hex = ciphertext_hex.decode("ascii").strip()
        else:
            cipher_hex = (ciphertext_hex or "").strip()
        ciphertext = bytes.fromhex(cipher_hex)
        aesgcm = AESGCM(key)
        try:
            return aesgcm.decrypt(iv, ciphertext + tag, None)
        except InvalidTag as exc:
            raise ValueError("HyperPay webhook authentication failed") from exc

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
