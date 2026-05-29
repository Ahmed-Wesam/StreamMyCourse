"""Contract tests: api-waf-stack.yaml REGIONAL WAF + API Gateway association."""

from __future__ import annotations

from pathlib import Path


def _api_waf_stack_text() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "templates"
        / "api-waf-stack.yaml"
    )
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_api_waf_stack_parameters() -> None:
    text = _api_waf_stack_text()
    for name in (
        "Environment:",
        "CatalogApiRestApiId:",
        "CatalogApiStageName:",
        "EnableWafApi:",
        "EnableManagedRulesBlock:",
        "ApiRateLimit:",
    ):
        assert name in text


def test_api_waf_stack_regional_web_acl_and_association() -> None:
    text = _api_waf_stack_text()
    assert "ApiWebAcl:" in text
    assert "Type: AWS::WAFv2::WebACL" in text
    assert "Scope: REGIONAL" in text
    assert "ApiWebAclAssociation:" in text
    assert "Type: AWS::WAFv2::WebACLAssociation" in text
    assert "arn:aws:apigateway:${AWS::Region}::/restapis/${RestApiId}/stages/${StageName}" in text


def test_api_waf_stack_courses_rate_rule_excludes_webhooks() -> None:
    text = _api_waf_stack_text()
    assert "CoursesRateLimitExcludeWebhooks" in text
    assert "RateBasedStatement:" in text
    assert "!Base64 '/courses'" in text
    assert "!Base64 '/webhooks'" in text
    assert "NotStatement:" in text


def test_api_waf_stack_managed_common_rule_set_count_by_default() -> None:
    text = _api_waf_stack_text()
    assert "AWSManagedRulesCommonRuleSet" in text
    assert "ManagedRuleGroupStatement:" in text
    assert "EnableManagedRulesBlock" in text
    assert "Count: {}" in text


def test_api_waf_stack_outputs() -> None:
    text = _api_waf_stack_text()
    assert "ApiWebAclArn:" in text
    assert "ApiWebAclId:" in text
    assert "!GetAtt ApiWebAcl.Arn" in text
    assert "!GetAtt ApiWebAcl.Id" in text
