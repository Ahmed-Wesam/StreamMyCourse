"""Contract: CatalogApiStage MethodSettings use valid API Gateway path keys."""

from __future__ import annotations

from pathlib import Path


def _api_stack_text() -> str:
    path = Path(__file__).resolve().parents[2] / "infrastructure" / "templates" / "api-stack.yaml"
    return path.read_text(encoding="utf-8")


def test_webhook_throttles_use_explicit_post_paths_not_star_star() -> None:
    """ResourcePath ending in /* with HttpMethod * is rejected by API Gateway (webhooks/*/*)."""
    text = _api_stack_text()
    assert "ResourcePath: '/webhooks/*'" not in text
    stage_block = text.split("CatalogApiStage:")[1]
    for path in (
        "ResourcePath: '/webhooks/kinescope'",
        "ResourcePath: '/webhooks/kinescope/drm-auth'",
        "ResourcePath: '/webhooks/payments/paytabs'",
    ):
        assert path in stage_block
    assert stage_block.count("HttpMethod: 'POST'") >= 3
