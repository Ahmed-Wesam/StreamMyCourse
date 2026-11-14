"""Contract: async queue workers use EventBridge poll schedule instead of always-on ESM."""

from __future__ import annotations

from pathlib import Path


def _read(rel: str) -> str:
    path = Path(__file__).resolve().parents[2] / rel
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_github_deploy_role_can_manage_worker_schedules() -> None:
    for rel in (
        "infrastructure/templates/github-deploy-role-stack.yaml",
        "infrastructure/iam-policy-github-deploy-backend.json",
    ):
        text = _read(rel)
        assert "EventsRulesStreamMyCourse" in text
        assert "events:*" in text
        assert "rule/StreamMyCourse-*" in text
        assert "DsqlClusterStackManage" in text
        assert "dsql:DbConnectAdmin" in text or "dsql:*" in text


def test_workers_check_each_queue_every_15_seconds() -> None:
    for rel in (
        "infrastructure/lambda/transactional_mail/sqs_scheduled_poll.py",
        "infrastructure/lambda/billing_fulfillment/sqs_scheduled_poll.py",
        "infrastructure/lambda/media_cleanup/sqs_scheduled_poll.py",
    ):
        text = _read(rel)
        assert "POLL_INTERVAL_SECONDS = 15" in text
        assert "POLL_PASSES = 4" in text


def test_transactional_mail_worker_timeout_covers_four_checks() -> None:
    text = _read("infrastructure/templates/transactional-mail-stack.yaml")
    assert "Timeout: 90" in text


def test_transactional_mail_stack_disables_esm_and_schedules_worker() -> None:
    text = _read("infrastructure/templates/transactional-mail-stack.yaml")
    assert "WORK_QUEUE_URL: !Ref TransactionalMailQueue" in text
    assert "TransactionalMailWorkerScheduleRule:" in text
    assert "rate(1 minute)" in text
    esm = text.split("TransactionalMailEventSourceMapping:")[1].split("TransactionalMailWorkerScheduleRule:")[0]
    assert "Enabled: false" in esm


def test_media_cleanup_stack_disables_esm_and_schedules_worker() -> None:
    text = _read("infrastructure/templates/media-cleanup-stack.yaml")
    assert "WORK_QUEUE_URL: !Ref MediaCleanupQueue" in text
    assert "MediaCleanupWorkerScheduleRule:" in text
    assert "rate(1 minute)" in text
    esm = text.split("MediaCleanupEventSourceMapping:")[1].split("MediaCleanupWorkerScheduleRule:")[0]
    assert "Enabled: false" in esm


def test_payments_stack_disables_esm_and_schedules_fulfillment() -> None:
    text = _read("infrastructure/templates/payments-stack.yaml")
    assert "WORK_QUEUE_URL: !Ref BillingFulfillmentQueue" in text
    assert "BillingFulfillmentScheduleRule:" in text
    assert "rate(1 minute)" in text
    esm = text.split("BillingFulfillmentEventSourceMapping:")[1].split("BillingFulfillmentScheduleRule:")[0]
    assert "Enabled: false" in esm