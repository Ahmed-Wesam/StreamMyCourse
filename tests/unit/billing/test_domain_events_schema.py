"""W3-P1 — BillingDomainEvent schema v1 serialize/parse."""

from __future__ import annotations

import pytest

from domain.events import SCHEMA_VERSION, BillingDomainEvent


def _sample_event(**overrides: object) -> BillingDomainEvent:
    base = dict(
        event_type="purchase.paid",
        provider="hyperpay",
        provider_event_id="hyperpay:pay-1:000.000.000",
        environment="dev",
        user_sub="cognito-sub-1",
        plan_id="",
        payload_digest="a" * 64,
        purchase_id="c0000000-0000-4000-8000-000000000001",
    )
    base.update(overrides)
    return BillingDomainEvent(**base)  # type: ignore[arg-type]


def test_schema_version_is_one() -> None:
    assert SCHEMA_VERSION == 1
    event = _sample_event()
    assert event.schema_version == 1


def test_to_sqs_dict_includes_required_fields() -> None:
    event = _sample_event(amount_minor=50_000, currency="JOD")
    data = event.to_sqs_dict()
    assert data["schema_version"] == 1
    assert data["event_type"] == "purchase.paid"
    assert data["provider"] == "hyperpay"
    assert data["purchase_id"] == "c0000000-0000-4000-8000-000000000001"
    assert data["amount_minor"] == 50_000
    assert data["currency"] == "JOD"


def test_to_sqs_dict_omits_unset_optional_fields() -> None:
    data = _sample_event().to_sqs_dict()
    assert "provider_subscription_id" not in data
    assert "canceled_at" not in data


def test_from_sqs_dict_round_trip() -> None:
    original = _sample_event(provider_tran_ref="pay-1")
    restored = BillingDomainEvent.from_sqs_dict(original.to_sqs_dict())
    assert restored == original


def test_rejects_unknown_event_type() -> None:
    with pytest.raises(ValueError, match="event_type"):
        _sample_event(event_type="purchase.unknown")


def test_purchase_revoked_event_type_allowed() -> None:
    event = _sample_event(event_type="purchase.revoked", provider_tran_ref="orig-pay")
    assert event.event_type == "purchase.revoked"
