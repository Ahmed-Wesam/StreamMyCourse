"""Neutral billing domain events (WS3) — duplicated from billing_edge for independent zips."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

SCHEMA_VERSION = 1

_PURCHASE_EVENT_TYPES = frozenset(
    {
        "purchase.paid",
        "purchase.failed",
        "purchase.revoked",
    }
)

_DOMAIN_EVENT_TYPES = _PURCHASE_EVENT_TYPES


@dataclass(frozen=True)
class BillingDomainEvent:
    event_type: str
    provider: str
    provider_event_id: str
    environment: str
    user_sub: str
    plan_id: str
    payload_digest: str
    schema_version: int = SCHEMA_VERSION
    provider_subscription_id: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None
    canceled_at: Optional[str] = None
    purchase_id: Optional[str] = None
    product_type: Optional[str] = None
    course_id: Optional[str] = None
    amount_minor: Optional[int] = None
    currency: Optional[str] = None
    provider_tran_ref: Optional[str] = None

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version {self.schema_version}")
        if self.event_type not in _DOMAIN_EVENT_TYPES:
            raise ValueError(f"unsupported event_type {self.event_type!r}")

    def to_sqs_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "schema_version": self.schema_version,
            "event_type": self.event_type,
            "provider": self.provider,
            "provider_event_id": self.provider_event_id,
            "environment": self.environment,
            "user_sub": self.user_sub,
            "plan_id": self.plan_id,
            "payload_digest": self.payload_digest,
        }
        if self.provider_subscription_id is not None:
            data["provider_subscription_id"] = self.provider_subscription_id
        if self.current_period_start is not None:
            data["current_period_start"] = self.current_period_start
        if self.current_period_end is not None:
            data["current_period_end"] = self.current_period_end
        if self.cancel_at_period_end is not None:
            data["cancel_at_period_end"] = self.cancel_at_period_end
        if self.canceled_at is not None:
            data["canceled_at"] = self.canceled_at
        if self.purchase_id is not None:
            data["purchase_id"] = self.purchase_id
        if self.product_type is not None:
            data["product_type"] = self.product_type
        if self.course_id is not None:
            data["course_id"] = self.course_id
        if self.amount_minor is not None:
            data["amount_minor"] = self.amount_minor
        if self.currency is not None:
            data["currency"] = self.currency
        if self.provider_tran_ref is not None:
            data["provider_tran_ref"] = self.provider_tran_ref
        return data

    @classmethod
    def from_sqs_dict(cls, data: Dict[str, Any]) -> BillingDomainEvent:
        return cls(
            schema_version=int(data["schema_version"]),
            event_type=str(data["event_type"]),
            provider=str(data["provider"]),
            provider_event_id=str(data["provider_event_id"]),
            environment=str(data["environment"]),
            user_sub=str(data["user_sub"]),
            plan_id=str(data["plan_id"]),
            payload_digest=str(data["payload_digest"]),
            provider_subscription_id=_optional_str(data, "provider_subscription_id"),
            current_period_start=_optional_str(data, "current_period_start"),
            current_period_end=_optional_str(data, "current_period_end"),
            cancel_at_period_end=_optional_bool(data, "cancel_at_period_end"),
            canceled_at=_optional_str(data, "canceled_at"),
            purchase_id=_optional_str(data, "purchase_id"),
            product_type=_optional_str(data, "product_type"),
            course_id=_optional_str(data, "course_id"),
            amount_minor=_optional_int(data, "amount_minor"),
            currency=_optional_str(data, "currency"),
            provider_tran_ref=_optional_str(data, "provider_tran_ref"),
        )

    def is_purchase_event(self) -> bool:
        return self.event_type in _PURCHASE_EVENT_TYPES


def _optional_str(data: Dict[str, Any], key: str) -> Optional[str]:
    if key not in data or data[key] is None:
        return None
    return str(data[key])


def _optional_bool(data: Dict[str, Any], key: str) -> Optional[bool]:
    if key not in data or data[key] is None:
        return None
    return bool(data[key])


def _optional_int(data: Dict[str, Any], key: str) -> Optional[int]:
    if key not in data or data[key] is None:
        return None
    return int(data[key])
