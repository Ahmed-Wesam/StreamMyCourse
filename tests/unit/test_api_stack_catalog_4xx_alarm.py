"""Contract tests: catalog API Gateway 4XX CloudWatch alarm."""

from __future__ import annotations

from pathlib import Path


def _api_stack_text() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "templates"
        / "api-stack.yaml"
    )
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_api_stack_catalog_4xx_alarm_parameter_and_resource() -> None:
    text = _api_stack_text()
    assert "CatalogApi4xxAlarmThreshold:" in text
    assert "CatalogApi4xxAlarm:" in text
    assert "Type: AWS::CloudWatch::Alarm" in text
    assert "MetricName: 4XXError" in text
    assert "Namespace: AWS/ApiGateway" in text
    assert "StreamMyCourse-Catalog-${Environment}" in text
    assert "Threshold: !Ref CatalogApi4xxAlarmThreshold" in text


def test_api_stack_catalog_4xx_alarm_output() -> None:
    text = _api_stack_text()
    assert "CatalogApi4xxAlarmName:" in text
    assert "Value: !Ref CatalogApi4xxAlarm" in text
