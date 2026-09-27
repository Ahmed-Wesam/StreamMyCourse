"""W3-P5/P6 — billing fulfillment service (idempotency + environment gate)."""

from __future__ import annotations

import json
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
from service import FulfillmentRepository, process_domain_event  # noqa: E402


def _purchase_event(**overrides: object) -> BillingDomainEvent:
    base: dict[str, Any] = dict(
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
        self.writes = 0

    def process_event(self, event: BillingDomainEvent) -> Any:
        from service import FulfillmentResult

        if event.provider_event_id in self.seen:
            return FulfillmentResult(recorded=False, subscription_updated=False)
        self.seen.add(event.provider_event_id)
        self.writes += 1
        return FulfillmentResult(recorded=True, purchase_updated=True)


def test_duplicate_provider_event_id_does_not_call_repo_write_twice() -> None:
    repo = _TrackingRepo()
    evt = _purchase_event()
    process_domain_event(evt, _dev_config(), repo)
    process_domain_event(evt, _dev_config(), repo)
    assert repo.writes == 1


def test_environment_mismatch_skips_repo_and_returns_success() -> None:
    repo = MagicMock()
    result = process_domain_event(_purchase_event(environment="prod"), _dev_config(), repo)
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


def test_domain_event_from_sqs_dict_round_trip() -> None:
    evt = _purchase_event()
    restored = BillingDomainEvent.from_sqs_dict(json.loads(json.dumps(evt.to_sqs_dict())))
    assert restored == evt


def test_process_domain_event_delegates_matching_environment() -> None:
    repo = MagicMock()
    from service import FulfillmentResult

    repo.process_event.return_value = FulfillmentResult(recorded=True, purchase_updated=True)
    evt = _purchase_event()
    result = process_domain_event(evt, _dev_config(), repo)
    repo.process_event.assert_called_once_with(evt)
    assert result.purchase_updated is True
