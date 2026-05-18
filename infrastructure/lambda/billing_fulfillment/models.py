"""Fulfillment domain types (subscription RDS mutations)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain_events import BillingDomainEvent


@dataclass(frozen=True)
class SubscriptionUpdate:
    status: str
    plan_id: str
    provider: str
    provider_subscription_id: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    canceled_at: Optional[str] = None


def subscription_update_for_event(event: BillingDomainEvent) -> SubscriptionUpdate:
    """Map a domain event to ``user_subscriptions`` columns per access-policy-v1."""
    if event.event_type == "subscription.activated":
        return SubscriptionUpdate(
            status="active",
            plan_id=event.plan_id,
            provider=event.provider,
            provider_subscription_id=event.provider_subscription_id,
            current_period_start=event.current_period_start,
            current_period_end=event.current_period_end,
            cancel_at_period_end=False,
            canceled_at=None,
        )
    if event.event_type == "subscription.renewed":
        return SubscriptionUpdate(
            status="active",
            plan_id=event.plan_id,
            provider=event.provider,
            provider_subscription_id=event.provider_subscription_id,
            current_period_start=event.current_period_start,
            current_period_end=event.current_period_end,
            cancel_at_period_end=False,
            canceled_at=None,
        )
    if event.event_type == "subscription.payment_failed":
        return SubscriptionUpdate(
            status="past_due",
            plan_id=event.plan_id,
            provider=event.provider,
            provider_subscription_id=event.provider_subscription_id,
            current_period_start=event.current_period_start,
            current_period_end=event.current_period_end,
            cancel_at_period_end=False,
            canceled_at=None,
        )
    if event.event_type == "subscription.canceled":
        return SubscriptionUpdate(
            status="canceled",
            plan_id=event.plan_id,
            provider=event.provider,
            provider_subscription_id=event.provider_subscription_id,
            current_period_start=event.current_period_start,
            current_period_end=event.current_period_end,
            cancel_at_period_end=bool(event.cancel_at_period_end),
            canceled_at=event.canceled_at,
        )
    raise ValueError(f"not a subscription event: {event.event_type!r}")
