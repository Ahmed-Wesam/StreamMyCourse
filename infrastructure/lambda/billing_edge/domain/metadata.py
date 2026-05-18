"""Versioned cart_id metadata contract (WS3)."""

from __future__ import annotations

from dataclasses import dataclass


class EnvironmentMismatchError(Exception):
    """cart_id environment does not match deployment."""


class InvalidCartMetadataError(Exception):
    """cart_id missing or not parseable for a subscription IPN."""


class MissingSubscriptionPeriodError(Exception):
    """Granting Sale IPN lacks period end and cannot be derived."""


@dataclass(frozen=True)
class BillingMetadata:
    environment: str
    user_sub: str
    plan_id: str


def parse_cart_metadata(cart_id: str, deployment_environment: str) -> BillingMetadata:
    """Parse ``v1|{environment}|{user_sub}|{plan_id}`` from PayTabs cart_id."""
    parts = (cart_id or "").split("|")
    if len(parts) != 4 or parts[0] != "v1":
        raise ValueError("invalid cart_id metadata format")

    environment = parts[1].strip().lower()
    user_sub = parts[2].strip()
    plan_id = parts[3].strip()

    if not environment or not user_sub or not plan_id:
        raise ValueError("invalid cart_id metadata fields")

    deployment = deployment_environment.strip().lower()
    if environment != deployment:
        raise EnvironmentMismatchError(
            f"cart environment {environment!r} != deployment {deployment!r}"
        )

    return BillingMetadata(
        environment=environment,
        user_sub=user_sub,
        plan_id=plan_id,
    )
