"""W8-P8: payments-stack billing edge Lambda error alarm."""

from __future__ import annotations

from pathlib import Path


def _payments_stack_text() -> str:
    path = Path(__file__).resolve().parents[3] / "infrastructure" / "templates" / "payments-stack.yaml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_payments_stack_billing_edge_error_alarm() -> None:
    text = _payments_stack_text()
    assert "BillingEdgeErrorAlarm:" in text
    alarm_start = text.index("  BillingEdgeErrorAlarm:")
    alarm_end = text.index("  BillingFulfillmentEventSourceMapping:", alarm_start)
    alarm_block = text[alarm_start:alarm_end]
    assert "Namespace: AWS/Lambda" in alarm_block
    assert "MetricName: Errors" in alarm_block
    assert "FunctionName" in alarm_block
    assert "BillingEdge" in alarm_block
    assert "AlarmActions:" in alarm_block
    assert "BillingFulfillmentAlertTopic" in alarm_block
    assert "TreatMissingData: notBreaching" in alarm_block
    assert "StreamMyCourse-BillingEdge-${Environment}-Errors" in alarm_block
