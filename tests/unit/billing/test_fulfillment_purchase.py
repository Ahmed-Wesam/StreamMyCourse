"""RS-5 Slice D — purchase fulfillment mapping."""

from __future__ import annotations

import sys
from pathlib import Path

_FULFILL_SRC = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "lambda" / "billing_fulfillment"
)
if str(_FULFILL_SRC) not in sys.path:
    sys.path.append(str(_FULFILL_SRC))

from domain_events import BillingDomainEvent  # noqa: E402
from models import purchase_fulfillment_for_event  # noqa: E402


def _purchase_event(**overrides: object) -> BillingDomainEvent:
    base = dict(
        event_type="purchase.paid",
        provider="paytabs",
        provider_event_id="paytabs:TST1:A",
        environment="dev",
        user_sub="cognito-sub-1",
        plan_id="",
        payload_digest="a" * 64,
        purchase_id="c0000000-0000-4000-8000-000000000001",
        product_type="course",
        amount_minor=9900,
        currency="USD",
        provider_tran_ref="TST1",
    )
    base.update(overrides)
    return BillingDomainEvent(**base)  # type: ignore[arg-type]


def test_purchase_paid_maps_to_paid_status() -> None:
    target = purchase_fulfillment_for_event(_purchase_event())
    assert target.status == "paid"
    assert target.provider_tran_ref == "TST1"


def test_purchase_failed_maps_to_failed_status() -> None:
    target = purchase_fulfillment_for_event(_purchase_event(event_type="purchase.failed"))
    assert target.status == "failed"


def test_purchase_revoked_maps_to_revoked_status() -> None:
    target = purchase_fulfillment_for_event(
        _purchase_event(event_type="purchase.revoked", provider_tran_ref="ORIG-1")
    )
    assert target.status == "revoked"
    assert target.provider_tran_ref == "ORIG-1"
