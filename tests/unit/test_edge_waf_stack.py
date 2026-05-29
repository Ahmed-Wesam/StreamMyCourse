"""Contract tests: edge-waf-stack.yaml CLOUDFRONT WAF + student distribution association."""

from __future__ import annotations

from pathlib import Path


def _edge_waf_stack_text() -> str:
    path = (
        Path(__file__).resolve().parents[2]
        / "infrastructure"
        / "templates"
        / "edge-waf-stack.yaml"
    )
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_edge_waf_stack_parameters() -> None:
    text = _edge_waf_stack_text()
    for name in (
        "Environment:",
        "StudentDistributionId:",
        "EnableWafEdge:",
        "EdgeStaticRateLimit:",
    ):
        assert name in text


def test_edge_waf_stack_cloudfront_scope_and_association() -> None:
    text = _edge_waf_stack_text()
    assert "StudentEdgeWebAcl:" in text
    assert "Scope: CLOUDFRONT" in text
    assert "StudentEdgeWebAclAssociation:" in text
    assert "arn:aws:cloudfront::${AWS::AccountId}:distribution/${StudentDistributionId}" in text


def test_edge_waf_stack_static_flood_rate_rule() -> None:
    text = _edge_waf_stack_text()
    assert "StudentStaticFloodRateLimit" in text
    assert "EdgeStaticRateLimit" in text
    assert "EvaluationWindowSec: 300" in text
