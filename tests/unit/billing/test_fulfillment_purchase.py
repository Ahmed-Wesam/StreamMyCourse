"""RS-5 Slice D — purchase fulfillment mapping."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_FULFILL_SRC = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "lambda" / "billing_fulfillment"
)
if str(_FULFILL_SRC) not in sys.path:
    sys.path.append(str(_FULFILL_SRC))

from domain_events import BillingDomainEvent  # noqa: E402
from fulfillment_repo import _apply_purchase_update  # noqa: E402
from models import purchase_fulfillment_for_event  # noqa: E402


def _purchase_event(**overrides: object) -> BillingDomainEvent:
    base = dict(
        event_type="purchase.paid",
        provider="hyperpay",
        provider_event_id="hyperpay:TST1:A",
        environment="dev",
        user_sub="cognito-sub-1",
        plan_id="",
        payload_digest="a" * 64,
        purchase_id="c0000000-0000-4000-8000-000000000001",
        product_type="course",
        amount_minor=50_000,
        currency="JOD",
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


def test_purchase_paid_ipn_error_mentions_jod_not_usd() -> None:
    cur = MagicMock()
    cur.fetchone.return_value = (50_000, "JOD", "pending")
    event = _purchase_event(amount_minor=None, currency=None)
    target = purchase_fulfillment_for_event(event)
    with pytest.raises(ValueError, match="JOD amount and currency"):
        _apply_purchase_update(cur, event=event, target=target)


def test_purchase_uuid_webhook_locks_row_without_user_sub() -> None:
    cur = MagicMock()
    cur.fetchone.return_value = (50_000, "JOD", "pending")
    cur.rowcount = 1
    event = _purchase_event(user_sub="")
    target = purchase_fulfillment_for_event(event)
    updated = _apply_purchase_update(cur, event=event, target=target)
    assert updated is True
    select_sql = cur.execute.call_args_list[0].args[0]
    select_params = cur.execute.call_args_list[0].args[1]
    assert "user_sub" not in select_sql
    assert select_params == (target.purchase_id, "dev")
