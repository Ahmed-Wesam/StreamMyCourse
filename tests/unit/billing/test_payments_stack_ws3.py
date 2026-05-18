"""WS3-P8: payments-stack fulfillment RDS env, IAM, and DLQ alarm."""

from __future__ import annotations

from pathlib import Path


def _payments_stack_text() -> str:
    path = Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "payments-stack.yaml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_payments_stack_billing_fulfillment_dlq_alarm() -> None:
    text = _payments_stack_text()
    assert "BillingFulfillmentDlqAlarm:" in text
    assert "ApproximateNumberOfMessagesVisible" in text
    assert "BillingFulfillmentDlq" in text
    assert "BillingFulfillmentAlertTopic" in text
    alarm_start = text.index("  BillingFulfillmentDlqAlarm:")
    alarm_end = text.index("  BillingFulfillmentEventSourceMapping:", alarm_start)
    alarm_block = text[alarm_start:alarm_end]
    assert "AlarmActions:" in alarm_block
    assert "BillingFulfillmentAlertTopic" in alarm_block
    assert "BillingFulfillmentAlertEmail:" in text
    assert "BillingFulfillmentAlertEmailSubscription:" in text
    assert "HasBillingFulfillmentAlertEmail" in text


def test_payments_stack_fulfillment_db_env_and_deployment_environment() -> None:
    text = _payments_stack_text()
    start = text.index("  BillingFulfillment:")
    end = text.index("  BillingFulfillmentEventSourceMapping:", start)
    block = text[start:end]
    assert "DEPLOYMENT_ENVIRONMENT:" in block
    assert "DB_HOST:" in block
    assert "DB_PORT:" in block
    assert "DB_NAME:" in block
    assert "DB_SECRET_ARN:" in block
    assert "${RdsStackName}-DbHost" in block
    assert "${RdsStackName}-DbSecretArn" in block


def test_payments_stack_fulfillment_role_can_read_db_secret() -> None:
    text = _payments_stack_text()
    start = text.index("  BillingFulfillmentRole:")
    end = text.index("  BillingFulfillment:", start)
    block = text[start:end]
    assert "SecretsManagerRdsCreds" in block
    assert "secretsmanager:GetSecretValue" in block
    assert "${RdsStackName}-DbSecretArn" in block
