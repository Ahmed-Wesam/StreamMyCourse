"""Video provider edge CORS origin selection."""

from __future__ import annotations

from typing import Any, Dict

from video_edge_config import VideoProviderEdgeConfig
from video_provider_edge._imports import video_edge_handler


def _cfg(**overrides: Any) -> VideoProviderEdgeConfig:
    base: Dict[str, Any] = {
        "deployment_environment": "dev",
        "catalog_lambda_arn": "arn:aws:lambda:eu-west-1:1:function:catalog",
        "kinescope_api_token": "token",
        "kinescope_parent_id": "parent",
        "kinescope_webhook_secret": None,
        "cors_allow_origin": None,
    }
    base.update(overrides)
    return VideoProviderEdgeConfig(**base)


def test_pick_cors_origin_reflects_request_when_allowlist_unset() -> None:
    event = {"headers": {"Origin": "https://teach.dev.researchspectrum.org"}}
    assert (
        video_edge_handler._pick_cors_origin(event, _cfg())
        == "https://teach.dev.researchspectrum.org"
    )


def test_pick_cors_origin_matches_csv_allowlist() -> None:
    event = {"headers": {"Origin": "https://teach.dev.researchspectrum.org"}}
    cfg = _cfg(
        cors_allow_origin=(
            "https://teach.dev.researchspectrum.org,https://learn.dev.researchspectrum.org"
        )
    )
    assert video_edge_handler._pick_cors_origin(event, cfg) == (
        "https://teach.dev.researchspectrum.org"
    )


def test_pick_cors_origin_falls_back_to_first_allowlist_entry() -> None:
    event = {"headers": {"Origin": "https://unknown.example.com"}}
    cfg = _cfg(cors_allow_origin="https://teach.dev.researchspectrum.org")
    assert video_edge_handler._pick_cors_origin(event, cfg) == (
        "https://teach.dev.researchspectrum.org"
    )
