"""Contract tests: deploy-backend.sh video provider edge ordering."""

from __future__ import annotations

from pathlib import Path


def _deploy_backend_sh_text() -> str:
    path = Path(__file__).resolve().parents[2] / "scripts" / "deploy-backend.sh"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_deploy_backend_sh_preflights_edge_before_api_when_catalog_exists() -> None:
    text = _deploy_backend_sh_text()
    preflight = text.index("Pre-deploy: refreshing video provider edge")
    phase_a = text.index('_deploy_api_stack "phase A"')
    assert preflight < phase_a


def test_deploy_backend_sh_first_time_wires_edge_after_catalog() -> None:
    text = _deploy_backend_sh_text()
    phase_a = text.index('_deploy_api_stack "phase A"')
    first_time = text.index("first-time wiring")
    wire = text.index('_deploy_api_stack "wire video edge routes"')
    assert phase_a < first_time < wire


def test_deploy_backend_sh_skips_duplicate_wire_when_preflight_set() -> None:
    text = _deploy_backend_sh_text()
    assert "pre-deploy refresh" in text
    assert "((${#VIDEO_EDGE_PARAM_OVERRIDES[@]} == 0))" in text


def test_deploy_backend_sh_video_edge_only_when_kinescope() -> None:
    text = _deploy_backend_sh_text()
    block = text[
        text.index("# Video provider edge (Kinescope): first-time env only")
        : text.index("Video provider edge routes wired in catalog deploy")
    ]
    assert '[[ "$VIDEO_PROVIDER" == "kinescope"' in block
    assert "deploy-video-provider-edge.sh" in block
    assert "VIDEO_EDGE_STACK" in block
    assert "VideoProviderEdgeLambdaArn" in block


def test_deploy_backend_sh_exports_kinescope_secrets_for_edge_stack() -> None:
    text = _deploy_backend_sh_text()
    preflight = text[
        text.index('export CATALOG_LAMBDA_ARN="$PREFLIGHT_CATALOG_ARN"')
        : text.index("Pre-deploy: refreshing video provider edge")
    ]
    assert "export CORS_ALLOW_ORIGIN" in preflight


def test_deploy_backend_sh_passes_video_edge_arn_to_api_stack() -> None:
    text = _deploy_backend_sh_text()
    assert "VIDEO_EDGE_PARAM_OVERRIDES" in text
    assert '"VideoProviderEdgeLambdaArn=${VIDEO_EDGE_ARN}"' in text
    assert "${VIDEO_EDGE_PARAM_OVERRIDES[@]}" in text
