"""Purchase correlation for HyperPay merchantTransactionId.

Live checkouts send the purchase UUID. The acquirer accepts only
``[A-Za-z0-9_-]`` and at most 41 characters, so the older
``v2|env|user|...`` cart string is rejected on the live bank path.
Webhook parsing still accepts that v2 string for notifications that
already used it.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

# HyperPay live acquirer limit (hyphen and underscore are allowed).
MERCHANT_TRANSACTION_ID_MAX_LENGTH = 41
_MERCHANT_TX_RE = re.compile(r"^[A-Za-z0-9_-]{1,41}$")


class EnvironmentMismatchError(Exception):
    """cart_id environment does not match deployment."""


class InvalidCartMetadataError(Exception):
    """cart_id missing or not parseable for a purchase notification."""


@dataclass(frozen=True)
class BillingMetadata:
    environment: str
    user_sub: str
    plan_id: str = ""
    product_type: str = ""
    course_id: str | None = None
    purchase_id: str = ""

    @property
    def is_purchase(self) -> bool:
        if not self.purchase_id:
            return False
        if self.product_type in ("course", "bundle"):
            return True
        # Live merchantTransactionId is only the purchase UUID. Fulfillment
        # loads user_sub, product type, and course from that row.
        return self.product_type == "" and self.user_sub == ""


def bank_safe_merchant_transaction_id(purchase_id: str) -> str:
    """Return a purchase UUID HyperPay can forward to the live acquirer."""
    raw = (purchase_id or "").strip()
    try:
        canonical = str(uuid.UUID(raw))
    except ValueError as exc:
        raise ValueError("purchase_id cannot be used as merchantTransactionId") from exc
    if len(canonical) > MERCHANT_TRANSACTION_ID_MAX_LENGTH or not _MERCHANT_TX_RE.fullmatch(
        canonical
    ):
        raise ValueError("purchase_id cannot be used as merchantTransactionId")
    return canonical


def purchase_reference_metadata(
    merchant_transaction_id: str,
    deployment_environment: str,
) -> BillingMetadata:
    """Map an echoed purchase UUID to metadata. The purchase row fills the rest."""
    environment = (deployment_environment or "").strip().lower()
    if not environment:
        raise ValueError("deployment environment is required")
    return BillingMetadata(
        environment=environment,
        user_sub="",
        purchase_id=bank_safe_merchant_transaction_id(merchant_transaction_id),
    )


def parse_cart_metadata(cart_id: str, deployment_environment: str) -> BillingMetadata:
    """Parse a legacy ``v2|...`` cart string from an older HyperPay notification."""
    parts = (cart_id or "").split("|")
    if not parts or parts[0] != "v2":
        raise ValueError("invalid cart_id metadata format")

    deployment = deployment_environment.strip().lower()

    if len(parts) == 6 and parts[3] == "course":
        environment = parts[1].strip().lower()
        user_sub = parts[2].strip()
        course_id = parts[4].strip()
        purchase_id = parts[5].strip()
        if not environment or not user_sub or not course_id or not purchase_id:
            raise ValueError("invalid cart_id metadata fields")
        if environment != deployment:
            raise EnvironmentMismatchError(
                f"cart environment {environment!r} != deployment {deployment!r}"
            )
        return BillingMetadata(
            environment=environment,
            user_sub=user_sub,
            product_type="course",
            course_id=course_id,
            purchase_id=purchase_id,
        )

    if len(parts) == 5 and parts[3] == "bundle":
        environment = parts[1].strip().lower()
        user_sub = parts[2].strip()
        purchase_id = parts[4].strip()
        if not environment or not user_sub or not purchase_id:
            raise ValueError("invalid cart_id metadata fields")
        if environment != deployment:
            raise EnvironmentMismatchError(
                f"cart environment {environment!r} != deployment {deployment!r}"
            )
        return BillingMetadata(
            environment=environment,
            user_sub=user_sub,
            product_type="bundle",
            purchase_id=purchase_id,
        )

    raise ValueError("invalid cart_id metadata format")
