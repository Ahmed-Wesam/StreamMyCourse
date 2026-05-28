"""Catalog fallback when Kinescope HTTP routes hit the VPC Lambda."""

from __future__ import annotations

import json
from unittest.mock import patch

from config import AppConfig
from index import lambda_handler
from services.course_management.kinescope_routing import kinescope_http_routed_on_catalog


def _kinescope_cfg() -> AppConfig:
    return AppConfig(
        video_bucket="bucket",
        default_mp4_url="https://example.com/default.mp4",
        video_url="https://example.com",
        allowed_origins=["https://teacher.example.com"],
        video_provider="kinescope",
    )


def test_kinescope_routing_ignores_s3_provider() -> None:
    cfg = AppConfig(
        video_bucket="bucket",
        default_mp4_url="https://example.com/default.mp4",
        video_url="https://example.com",
        allowed_origins=["*"],
        video_provider="s3",
    )
    assert not kinescope_http_routed_on_catalog(cfg, method="POST", parts=["upload-url"])


def test_kinescope_routing_detects_upload_url() -> None:
    cfg = _kinescope_cfg()
    assert kinescope_http_routed_on_catalog(cfg, method="POST", parts=["upload-url"])
    assert kinescope_http_routed_on_catalog(cfg, method="OPTIONS", parts=["upload-url"])
    assert not kinescope_http_routed_on_catalog(cfg, method="GET", parts=["upload-url"])


def test_catalog_upload_url_returns_video_edge_required() -> None:
    event = {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/upload-url",
        "headers": {"origin": "https://teacher.example.com"},
        "body": "{}",
    }
    bootstrap = (
        _kinescope_cfg(),
        object(),
        object(),
        None,
        None,
        None,
        None,
        None,
    )
    with patch("index.load_config", return_value=_kinescope_cfg()), patch(
        "index.lambda_bootstrap", return_value=bootstrap
    ), patch("index.check_student_session", return_value=None):
        resp = lambda_handler(event, None)

    assert resp["statusCode"] == 503
    body = json.loads(resp["body"])
    assert body["code"] == "video_edge_required"
