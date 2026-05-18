"""W3-P5/P6 — billing fulfillment service (idempotency + state matrix)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_FULFILL_SRC = (
    Path(__file__).resolve().parents[3] / "infrastructure" / "lambda" / "billing_fulfillment"
)
if str(_FULFILL_SRC) not in sys.path:
    sys.path.append(str(_FULFILL_SRC))

from fulfillment_config import FulfillmentConfig, load_fulfillment_config  # noqa: E402
from domain_events import BillingDomainEvent  # noqa: E402
from models import subscription_update_for_event  # noqa: E402
from service import FulfillmentRepository, process_domain_event  # noqa: E402


def _event(**overrides: object) -> BillingDomainEvent:
    base: dict[str, Any] = dict(
        event_type="subscription.activated",
        provider="paytabs",
        provider_event_id="paytabs:TST1:A",
        environment="dev",
        user_sub="cognito-sub-1",
        plan_id="a0000000-0000-4000-8000-000000000011",
        payload_digest="a" * 64,
    )
    base.update(overrides)
    return BillingDomainEvent(**base)  # type: ignore[arg-type]


def _dev_config() -> FulfillmentConfig:
    return FulfillmentConfig(
        deployment_environment="dev",
        db_secret_arn="arn:test",
        db_host="db.test",
        db_name="app",
        db_port=5432,
    )


class _TrackingRepo(FulfillmentRepository):
    """In-memory repo that dedupes on provider_event_id for service-level idempotency tests."""

    def __init__(self) -> None:
        self.seen: set[str] = set()
        self.subscription_writes = 0

    def process_event(self, event: BillingDomainEvent) -> Any:
        from service import FulfillmentResult

        if event.provider_event_id in self.seen:
            return FulfillmentResult(recorded=False, subscription_updated=False)
        self.seen.add(event.provider_event_id)
        self.subscription_writes += 1
        return FulfillmentResult(recorded=True, subscription_updated=True)


def test_duplicate_provider_event_id_does_not_call_subscription_write_twice() -> None:
    repo = _TrackingRepo()
    evt = _event()
    process_domain_event(evt, _dev_config(), repo)
    process_domain_event(evt, _dev_config(), repo)
    assert repo.subscription_writes == 1


def test_environment_mismatch_skips_repo_and_returns_success() -> None:
    repo = MagicMock()
    result = process_domain_event(_event(environment="prod"), _dev_config(), repo)
    repo.process_event.assert_not_called()
    assert result.skipped_environment is True
    assert result.recorded is False
    assert result.subscription_updated is False


def test_load_fulfillment_config_reads_deployment_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "prod")
    monkeypatch.setenv("DB_HOST", "db.internal")
    monkeypatch.setenv("DB_SECRET_ARN", "arn:secret")
    cfg = load_fulfillment_config()
    assert cfg.deployment_environment == "prod"
    assert cfg.db_host == "db.internal"
    assert cfg.db_secret_arn == "arn:secret"


@pytest.mark.parametrize(
    ("event_type", "expected_status", "extra"),
    [
        ("subscription.activated", "active", {}),
        ("subscription.renewed", "active", {}),
        ("subscription.payment_failed", "past_due", {}),
        ("subscription.canceled", "canceled", {"cancel_at_period_end": False}),
    ],
)
def test_subscription_update_status_per_event_type(
    event_type: str,
    expected_status: str,
    extra: dict[str, object],
) -> None:
    evt = _event(
        event_type=event_type,
        provider_subscription_id="AGR-1",
        current_period_start="2026-05-01T00:00:00Z",
        current_period_end="2026-06-01T00:00:00Z",
        **extra,
    )
    update = subscription_update_for_event(evt)
    assert update.status == expected_status
    assert update.plan_id == evt.plan_id
    assert update.provider == "paytabs"
    assert update.provider_subscription_id == "AGR-1"
    assert update.current_period_start == "2026-05-01T00:00:00Z"
    assert update.current_period_end == "2026-06-01T00:00:00Z"


def test_activated_clears_cancel_fields() -> None:
    update = subscription_update_for_event(
        _event(
            event_type="subscription.activated",
            cancel_at_period_end=True,
            canceled_at="2026-05-01T00:00:00Z",
        )
    )
    assert update.cancel_at_period_end is False
    assert update.canceled_at is None


def test_canceled_end_of_period_retains_period_and_cancel_flag() -> None:
    evt = _event(
        event_type="subscription.canceled",
        cancel_at_period_end=True,
        canceled_at="2026-05-18T12:00:00Z",
        current_period_end="2026-06-01T00:00:00Z",
    )
    update = subscription_update_for_event(evt)
    assert update.status == "canceled"
    assert update.cancel_at_period_end is True
    assert update.canceled_at == "2026-05-18T12:00:00Z"
    assert update.current_period_end == "2026-06-01T00:00:00Z"


def test_canceled_immediate_has_no_period_access_fields() -> None:
    evt = _event(
        event_type="subscription.canceled",
        cancel_at_period_end=False,
        canceled_at="2026-05-18T12:00:00Z",
        current_period_start=None,
        current_period_end=None,
    )
    update = subscription_update_for_event(evt)
    assert update.status == "canceled"
    assert update.cancel_at_period_end is False
    assert update.canceled_at == "2026-05-18T12:00:00Z"


def test_domain_event_from_sqs_dict_round_trip() -> None:
    evt = _event(provider_subscription_id="AGR-9")
    restored = BillingDomainEvent.from_sqs_dict(json.loads(json.dumps(evt.to_sqs_dict())))
    assert restored == evt


def test_process_domain_event_delegates_matching_environment() -> None:
    repo = MagicMock()
    from service import FulfillmentResult

    repo.process_event.return_value = FulfillmentResult(recorded=True, subscription_updated=True)
    evt = _event()
    result = process_domain_event(evt, _dev_config(), repo)
    repo.process_event.assert_called_once_with(evt)
    assert result.subscription_updated is True
