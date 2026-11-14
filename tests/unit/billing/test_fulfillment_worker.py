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
        event_type="purchase.paid",
        provider="hyperpay",
        provider_event_id="hyperpay:W1:A",
        environment="dev",
        user_sub="sub-1",
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


def test_worker_reports_batch_failure_on_environment_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(
        deployment_environment="dev",
        dsql_endpoint="example.dsql.eu-west-1.on.aws",
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


def test_worker_accepts_dsql_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(
        deployment_environment="prod",
        dsql_endpoint="example.dsql.eu-west-1.on.aws",
    )
    monkeypatch.setattr(worker, "_config_loader", lambda: cfg)
    result = worker.lambda_handler({"Records": []}, None)
    assert result == {"batchItemFailures": []}


def test_worker_rejects_missing_dsql_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(deployment_environment="prod", dsql_endpoint="")
    monkeypatch.setattr(worker, "_config_loader", lambda: cfg)
    with pytest.raises(RuntimeError, match="DSQL_ENDPOINT"):
        worker.lambda_handler({"Records": []}, None)


def test_worker_rejects_db_host_only(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(deployment_environment="prod", dsql_endpoint="")
    monkeypatch.setenv("DB_HOST", "rds.example")
    monkeypatch.setattr(worker, "_config_loader", lambda: cfg)
    with pytest.raises(RuntimeError, match="DSQL_ENDPOINT"):
        worker.lambda_handler({"Records": []}, None)


def test_worker_rejects_both_dsql_and_rds_env(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(
        deployment_environment="prod",
        dsql_endpoint="example.dsql.eu-west-1.on.aws",
    )
    monkeypatch.setenv("DB_HOST", "rds.example")
    monkeypatch.setattr(worker, "_config_loader", lambda: cfg)
    with pytest.raises(RuntimeError, match="DSQL_ENDPOINT only"):
        worker.lambda_handler({"Records": []}, None)


def test_worker_returns_batch_failure_on_processing_error(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = FulfillmentConfig(
        deployment_environment="dev",
        dsql_endpoint="example.dsql.eu-west-1.on.aws",
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
