"""W3-P1 — BillingDomainEvent schema v1 serialize/parse."""

from __future__ import annotations

import pytest

from domain.events import SCHEMA_VERSION, BillingDomainEvent


def _sample_event(**overrides: object) -> BillingDomainEvent:
    base = dict(
        event_type="subscription.activated",
        provider="paytabs",
        provider_event_id="paytabs:TST1:A",
        environment="dev",
        user_sub="cognito-sub-1",
        plan_id="00000000-0000-4000-8000-000000000001",
        payload_digest="a" * 64,
    )
    base.update(overrides)
    return BillingDomainEvent(**base)  # type: ignore[arg-type]


def test_schema_version_is_one() -> None:
    assert SCHEMA_VERSION == 1
    event = _sample_event()
    assert event.schema_version == 1


def test_to_sqs_dict_includes_required_fields() -> None:
    event = _sample_event(
        provider_subscription_id="AGR-1",
        current_period_start="2026-05-01T00:00:00Z",
        current_period_end="2026-06-01T00:00:00Z",
    )
    data = event.to_sqs_dict()
    assert data["schema_version"] == 1
    assert data["event_type"] == "subscription.activated"
    assert data["provider"] == "paytabs"
    assert data["provider_event_id"] == "paytabs:TST1:A"
    assert data["environment"] == "dev"
    assert data["user_sub"] == "cognito-sub-1"
    assert data["plan_id"] == "00000000-0000-4000-8000-000000000001"
    assert data["payload_digest"] == "a" * 64
    assert data["provider_subscription_id"] == "AGR-1"
    assert data["current_period_start"] == "2026-05-01T00:00:00Z"
    assert data["current_period_end"] == "2026-06-01T00:00:00Z"


def test_to_sqs_dict_omits_unset_optional_fields() -> None:
    data = _sample_event().to_sqs_dict()
    assert "provider_subscription_id" not in data
    assert "canceled_at" not in data


def test_from_sqs_dict_round_trip() -> None:
    original = _sample_event(cancel_at_period_end=True, canceled_at="2026-05-18T12:00:00Z")
    restored = BillingDomainEvent.from_sqs_dict(original.to_sqs_dict())
    assert restored == original


def test_rejects_unknown_event_type() -> None:
    with pytest.raises(ValueError, match="event_type"):
        _sample_event(event_type="subscription.unknown")
