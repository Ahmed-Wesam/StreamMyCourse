"""billing_fulfillment SQS worker (WS3)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from billing._imports import billing_fulfillment_worker as worker
from domain_events import BillingDomainEvent
from fulfillment_config import FulfillmentConfig


def _event_dict(**overrides: object) -> BillingDomainEvent:
    base = dict(
        event_type="subscription.activated",
        provider="paytabs",
        provider_event_id="paytabs:W1:A",
        environment="dev",
        user_sub="sub-1",
        plan_id="a0000000-0000-4000-8000-000000000011",
        payload_digest="a" * 64,
    )
    base.update(overrides)
    return BillingDomainEvent(**base)  # type: ignore[arg-type]


def test_worker_reports_batch_failure_on_environment_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(
        deployment_environment="dev",
        db_secret_arn="arn:test",
        db_host="db.test",
        db_name="app",
        db_port=5432,
    )
    repo = MagicMock()
    monkeypatch.setattr(worker, "_config_loader", lambda: cfg)
    monkeypatch.setattr(worker, "_repo_factory", lambda _cfg: repo)

    body = json.dumps(
        _event_dict(environment="prod").to_sqs_dict(),
        separators=(",", ":"),
    )
    result = worker.lambda_handler(
        {"Records": [{"messageId": "msg-env-1", "body": body}]},
        None,
    )
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-env-1"}]}
    repo.process_event.assert_not_called()


def test_worker_returns_batch_failure_on_processing_error(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(
        deployment_environment="dev",
        db_secret_arn="arn:test",
        db_host="db.test",
        db_name="app",
        db_port=5432,
    )
    repo = MagicMock()
    repo.process_event.side_effect = RuntimeError("db down")
    monkeypatch.setattr(worker, "_config_loader", lambda: cfg)
    monkeypatch.setattr(worker, "_repo_factory", lambda _cfg: repo)

    body = json.dumps(_event_dict().to_sqs_dict(), separators=(",", ":"))
    result = worker.lambda_handler(
        {"Records": [{"messageId": "msg-err-1", "body": body}]},
        None,
    )
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-err-1"}]}
