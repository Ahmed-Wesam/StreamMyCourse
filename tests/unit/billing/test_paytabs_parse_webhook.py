"""W3-P2 — PayTabs parse_webhook mapping."""

from __future__ import annotations

import json

import pytest

from domain.metadata import EnvironmentMismatchError, InvalidCartMetadataError
from providers.paytabs_adapter import IGNORED_TRAN_TYPES, PayTabsAdapter, parse_paytabs_webhook

_PLAN_ID = "00000000-0000-4000-8000-000000000001"
_USER_SUB = "student-sub-1"
_CART_DEV = f"v1|dev|{_USER_SUB}|{_PLAN_ID}"
_DIGEST = "d" * 64


def _body(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _parse(payload: dict, *, deployment: str = "dev") -> list:
    return parse_paytabs_webhook(
        _body(payload),
        deployment_environment=deployment,
        payload_digest=_DIGEST,
    )


def test_sale_authorized_maps_to_activated() -> None:
    events = _parse(
        {
            "tran_ref": "TST-ACT-100",
            "tran_type": "Sale",
            "payment_result": "A",
            "cart_id": _CART_DEV,
            "agreement_id": "AGR-100",
            "is_recurring": False,
            "transaction_time": "2026-05-18T12:00:00Z",
        }
    )
    assert len(events) == 1
    event = events[0]
    assert event.event_type == "subscription.activated"
    assert event.provider_event_id == "paytabs:TST-ACT-100:A"
    assert event.user_sub == _USER_SUB
    assert event.plan_id == _PLAN_ID
    assert event.provider_subscription_id == "AGR-100"
    assert event.payload_digest == _DIGEST
    assert event.current_period_end is not None


def test_renewal_sale_maps_to_renewed() -> None:
    events = _parse(
        {
            "tran_ref": "TST-REN-200",
            "tran_type": "Sale",
            "payment_result": "A",
            "cart_id": _CART_DEV,
            "agreement_id": "AGR-100",
            "is_recurring": True,
            "recurring_count": 2,
            "transaction_time": "2026-06-18T12:00:00Z",
        }
    )
    assert len(events) == 1
    assert events[0].event_type == "subscription.renewed"
    assert events[0].provider_event_id == "paytabs:TST-REN-200:A"


def test_recurring_count_one_maps_to_renewed() -> None:
    events = _parse(
        {
            "tran_ref": "TST-REN-201",
            "tran_type": "Sale",
            "payment_result": "A",
            "cart_id": _CART_DEV,
            "recurring_count": 1,
            "transaction_time": "2026-06-18T12:00:00Z",
        }
    )
    assert len(events) == 1
    assert events[0].event_type == "subscription.renewed"


def test_declined_sale_maps_to_payment_failed() -> None:
    events = _parse(
        {
            "tran_ref": "TST-DEC-300",
            "tran_type": "Sale",
            "payment_result": "D",
            "cart_id": _CART_DEV,
            "transaction_time": "2026-05-18T12:00:00Z",
        }
    )
    assert len(events) == 1
    assert events[0].event_type == "subscription.payment_failed"
    assert events[0].provider_event_id == "paytabs:TST-DEC-300:D"
    assert events[0].current_period_end is not None


def test_agreement_cancel_maps_to_canceled() -> None:
    events = _parse(
        {
            "tran_ref": "TST-CAN-400",
            "tran_type": "Agreement",
            "agreement_action": "cancelled",
            "cart_id": _CART_DEV,
            "agreement_id": "AGR-100",
        }
    )
    assert len(events) == 1
    assert events[0].event_type == "subscription.canceled"
    assert events[0].provider_event_id == "paytabs:AGR-100:canceled"


def test_ignored_tran_type_returns_empty() -> None:
    for tran_type in IGNORED_TRAN_TYPES:
        events = _parse(
            {
                "tran_ref": f"T-{tran_type}",
                "tran_type": tran_type,
                "payment_result": "A",
                "cart_id": _CART_DEV,
            }
        )
        assert events == [], f"expected ignore for {tran_type}"


def test_unknown_tran_type_with_cart_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError, match="unsupported tran_type"):
        _parse(
            {
                "tran_ref": "T-UNKNOWN",
                "tran_type": "Payout",
                "cart_id": _CART_DEV,
            }
        )


def test_provider_event_id_stable_for_same_ipn() -> None:
    payload = {
        "tran_ref": "TST-STABLE",
        "tran_type": "Sale",
        "payment_result": "A",
        "cart_id": _CART_DEV,
        "transaction_time": "2026-05-18T12:00:00Z",
    }
    first = _parse(payload)[0].provider_event_id
    second = _parse(payload)[0].provider_event_id
    assert first == second == "paytabs:TST-STABLE:A"


def test_nested_payment_result_object_supported() -> None:
    events = _parse(
        {
            "tran_ref": "TST-NESTED",
            "tran_type": "Sale",
            "payment_result": {
                "response_status": "A",
                "response_message": "Authorised",
            },
            "cart_id": _CART_DEV,
            "transaction_time": "2026-05-18T12:00:00Z",
        }
    )
    assert len(events) == 1
    assert events[0].provider_event_id == "paytabs:TST-NESTED:A"


def test_sale_without_cart_id_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError):
        _parse(
            {
                "tran_ref": "TST-NOCART",
                "tran_type": "Sale",
                "payment_result": "A",
            }
        )


def test_sale_with_malformed_cart_id_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError):
        _parse(
            {
                "tran_ref": "TST-BADCART",
                "tran_type": "Sale",
                "payment_result": "A",
                "cart_id": "not-versioned-metadata",
            }
        )


def test_sale_without_tran_ref_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError, match="tran_ref"):
        _parse(
            {
                "tran_type": "Sale",
                "payment_result": "A",
                "cart_id": _CART_DEV,
            }
        )


def test_sale_without_payment_result_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError, match="payment_result"):
        _parse(
            {
                "tran_ref": "TST-NOPR",
                "tran_type": "Sale",
                "cart_id": _CART_DEV,
            }
        )


def test_sale_unsupported_payment_result_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError, match="unsupported payment_result"):
        _parse(
            {
                "tran_ref": "TST-UNK",
                "tran_type": "Sale",
                "payment_result": "X",
                "cart_id": _CART_DEV,
            }
        )


def test_agreement_non_cancel_action_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError, match="unsupported Agreement action"):
        _parse(
            {
                "tran_ref": "TST-AGR",
                "tran_type": "Agreement",
                "agreement_action": "created",
                "cart_id": _CART_DEV,
                "agreement_id": "AGR-9",
            }
        )


def test_agreement_cancel_without_agreement_id_raises_invalid_metadata() -> None:
    with pytest.raises(InvalidCartMetadataError, match="agreement_id"):
        _parse(
            {
                "tran_ref": "TST-NOAGR",
                "tran_type": "Agreement",
                "agreement_action": "cancelled",
                "cart_id": _CART_DEV,
            }
        )


def test_environment_mismatch_raises() -> None:
    with pytest.raises(EnvironmentMismatchError):
        _parse(
            {
                "tran_ref": "TST-ENV",
                "tran_type": "Sale",
                "payment_result": "A",
                "cart_id": f"v1|prod|{_USER_SUB}|{_PLAN_ID}",
            },
            deployment="dev",
        )


def test_paytabs_adapter_delegates_to_parser() -> None:
    adapter = PayTabsAdapter(
        server_key="k",
        profile_id="p",
        api_domain="secure-jordan.paytabs.com",
        deployment_environment="dev",
    )
    events = adapter.parse_webhook(
        _body(
            {
                "tran_ref": "ADAPTER-1",
                "tran_type": "Sale",
                "payment_result": "A",
                "cart_id": _CART_DEV,
                "transaction_time": "2026-05-18T12:00:00Z",
            }
        ),
        deployment_environment="dev",
        payload_digest=_DIGEST,
    )
    assert len(events) == 1
