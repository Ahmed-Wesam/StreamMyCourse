"""Fulfillment domain types (purchase RDS mutations)."""

from __future__ import annotations

from dataclasses import dataclass

from domain_events import BillingDomainEvent


@dataclass(frozen=True)
class PurchaseFulfillmentTarget:
    purchase_id: str
    status: str
    provider_tran_ref: str | None = None


def purchase_fulfillment_for_event(event: BillingDomainEvent) -> PurchaseFulfillmentTarget:
    if not event.purchase_id:
        raise ValueError("purchase_id is required for purchase fulfillment")
    if event.event_type == "purchase.paid":
        return PurchaseFulfillmentTarget(
            purchase_id=event.purchase_id,
            status="paid",
            provider_tran_ref=event.provider_tran_ref,
        )
    if event.event_type == "purchase.failed":
        return PurchaseFulfillmentTarget(
            purchase_id=event.purchase_id,
            status="failed",
            provider_tran_ref=event.provider_tran_ref,
        )
    if event.event_type == "purchase.revoked":
        return PurchaseFulfillmentTarget(
            purchase_id=event.purchase_id,
            status="revoked",
            provider_tran_ref=event.provider_tran_ref,
        )
    raise ValueError(f"not a purchase event: {event.event_type!r}")
