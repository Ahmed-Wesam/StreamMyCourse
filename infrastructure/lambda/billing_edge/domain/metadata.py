"""Versioned cart_id metadata contract (RS-5 v2 one-time purchases)."""

from __future__ import annotations

from dataclasses import dataclass


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
        return bool(self.purchase_id and self.product_type in ("course", "bundle"))


def parse_cart_metadata(cart_id: str, deployment_environment: str) -> BillingMetadata:
    """Parse HyperPay ``merchantTransactionId`` (v2 one-time purchase cart_id)."""
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
