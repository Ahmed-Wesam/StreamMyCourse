"""Unit tests for `index.lambda_handler` (the Lambda entry point)."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

import index as index_mod
from config import AppConfig
from services.course_management.service import CourseManagementService


@pytest.fixture(autouse=True)
def _default_allowed_origins_for_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """Handler calls load_config() before bootstrap; tests need a non-empty allowlist."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "*")


def _bootstrap_returning(
    cfg: AppConfig,
    service: Optional[CourseManagementService],
    auth_service: Optional[Any] = None,
):
    """Factory: returns a `lambda_bootstrap` stand-in yielding fixed values."""

    def _stub() -> Tuple[AppConfig, Optional[CourseManagementService], Optional[Any]]:
        return cfg, service, auth_service

    return _stub


@pytest.fixture
def cfg_wildcard() -> AppConfig:
    return AppConfig(
        table_name="",
        video_bucket="",
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
        cognito_auth_enabled=False,
    )


class TestCorsAllowlistEmpty:
    def test_empty_allowlist_returns_503_and_skips_bootstrap(
        self, monkeypatch: pytest.MonkeyPatch, make_lambda_event
    ) -> None:
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        with patch.object(index_mod, "lambda_bootstrap") as mock_bs:
            evt = make_lambda_event(method="GET", path="/courses")
            resp = index_mod.lambda_handler(evt, None)
        mock_bs.assert_not_called()
        assert resp["statusCode"] == 503
        body = json.loads(resp["body"])
        assert body["code"] == "cors_misconfigured"
        assert "Access-Control-Allow-Origin" not in resp["headers"]

    def test_empty_allowlist_options_still_503(
        self, monkeypatch: pytest.MonkeyPatch, make_lambda_event
    ) -> None:
        monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
        with patch.object(index_mod, "lambda_bootstrap") as mock_bs:
            evt = make_lambda_event(method="OPTIONS", path="/courses", headers={"origin": "http://localhost:5173"})
            resp = index_mod.lambda_handler(evt, None)
        mock_bs.assert_not_called()
        assert resp["statusCode"] == 503
        assert "Access-Control-Allow-Origin" not in resp["headers"]


class TestServiceUnconfigured:
    def test_non_options_returns_503_with_catalog_unconfigured_code(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        monkeypatch.setattr(
            index_mod, "lambda_bootstrap", _bootstrap_returning(cfg_wildcard, None, None)
        )
        evt = make_lambda_event(method="GET", path="/courses")

        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 503
        body = json.loads(resp["body"])
        assert body["code"] == "catalog_unconfigured"
        assert "TABLE_NAME" in body["message"]
        # CORS headers must be present on the unconfigured response too.
        headers = resp["headers"]
        assert headers["Access-Control-Allow-Origin"] == "*"
        assert "OPTIONS" in headers["Access-Control-Allow-Methods"]

    def test_options_preflight_returns_204_with_cors_headers(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        monkeypatch.setattr(
            index_mod, "lambda_bootstrap", _bootstrap_returning(cfg_wildcard, None, None)
        )
        evt = make_lambda_event(
            method="OPTIONS",
            path="/courses",
            headers={"origin": "https://app.example.com"},
        )

        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 204
        assert resp["body"] == ""
        headers = resp["headers"]
        # Wildcard cfg with a real origin echoes the origin (per pick_origin).
        assert headers["Access-Control-Allow-Origin"] == "https://app.example.com"
        for verb in ("GET", "POST", "PUT", "DELETE", "OPTIONS"):
            assert verb in headers["Access-Control-Allow-Methods"]

    def test_uppercase_origin_header_also_recognized(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        # API Gateway normalizes header casing inconsistently between v1/v2,
        # so the handler reads both `origin` and `Origin`.
        monkeypatch.setattr(
            index_mod, "lambda_bootstrap", _bootstrap_returning(cfg_wildcard, None, None)
        )
        evt = make_lambda_event(
            method="GET",
            path="/courses",
            headers={"Origin": "https://capitalized.example.com"},
        )

        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 503
        assert (
            resp["headers"]["Access-Control-Allow-Origin"]
            == "https://capitalized.example.com"
        )

    def test_non_wildcard_cfg_with_unknown_origin_returns_first_allowed(
        self, monkeypatch: pytest.MonkeyPatch, make_lambda_event
    ) -> None:
        cfg = AppConfig(
            table_name="",
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["https://app.example.com", "http://localhost:5173"],
            cognito_auth_enabled=False,
        )
        monkeypatch.setattr(
            index_mod, "lambda_bootstrap", _bootstrap_returning(cfg, None, None)
        )
        evt = make_lambda_event(
            method="GET", path="/courses", headers={"origin": "https://evil.com"}
        )

        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 503
        assert (
            resp["headers"]["Access-Control-Allow-Origin"]
            == "https://app.example.com"
        )


class TestServiceConfigured:
    def test_delegates_to_course_management_handle(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        # Inject a configured service stub and verify the handler hands off.
        mock_service = MagicMock(spec=CourseManagementService)
        mock_service.list_published_courses.return_value = []
        mock_auth = MagicMock()

        monkeypatch.setattr(
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, mock_service, mock_auth),
        )

        evt = make_lambda_event(method="GET", path="/courses")
        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body == []

    def test_method_extracted_from_legacy_httpmethod_field(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
    ) -> None:
        monkeypatch.setattr(
            index_mod, "lambda_bootstrap", _bootstrap_returning(cfg_wildcard, None, None)
        )
        # API Gateway v1-style: `httpMethod` instead of `requestContext.http.method`.
        evt: Dict[str, Any] = {"httpMethod": "OPTIONS", "headers": {}}
        resp = index_mod.lambda_handler(evt, None)
        assert resp["statusCode"] == 204
