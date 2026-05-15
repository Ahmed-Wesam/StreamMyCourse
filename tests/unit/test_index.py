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
    progress_service: Optional[Any] = None,
    question_bank_service: Optional[Any] = None,
):
    """Factory: returns a `lambda_bootstrap` stand-in yielding fixed values."""

    def _stub() -> Tuple[
        AppConfig,
        Optional[CourseManagementService],
        Optional[Any],
        Optional[Any],
        Optional[Any],
    ]:
        return cfg, service, auth_service, progress_service, question_bank_service

    return _stub


@pytest.fixture
def cfg_wildcard() -> AppConfig:
    return AppConfig(
        video_bucket="",
        default_mp4_url="",
        video_url="",
        allowed_origins=["*"],
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
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, None, None, None),
        )
        evt = make_lambda_event(method="GET", path="/courses")

        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 503
        body = json.loads(resp["body"])
        assert body["code"] == "catalog_unconfigured"
        assert "DB_HOST" in body["message"]
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
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, None, None, None),
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
        for verb in ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
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
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, None, None, None),
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
            video_bucket="",
            default_mp4_url="",
            video_url="",
            allowed_origins=["https://app.example.com", "http://localhost:5173"],
        )
        monkeypatch.setattr(
            index_mod, "lambda_bootstrap", _bootstrap_returning(cfg, None, None, None)
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
        mock_progress = MagicMock()

        monkeypatch.setattr(
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, mock_service, mock_auth, mock_progress),
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
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, None, None, None),
        )
        # API Gateway v1-style: `httpMethod` instead of `requestContext.http.method`.
        evt: Dict[str, Any] = {"httpMethod": "OPTIONS", "headers": {}}
        resp = index_mod.lambda_handler(evt, None)
        assert resp["statusCode"] == 204


class TestProgressRouting:
    """Test routing for progress endpoints (GET /courses/{id}/progress, PUT /courses/{id}/lessons/{id}/progress)."""

    def test_get_course_progress_routes_to_controller_when_rds_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        """When RDS is enabled, GET /courses/{id}/progress should route to progress controller."""
        mock_service = MagicMock(spec=CourseManagementService)
        mock_auth = MagicMock()
        mock_progress = MagicMock()
        mock_progress.get_course_progress.return_value = {
            "courseId": "course-123",
            "totalReadyLessons": 5,
            "completedCount": 2,
            "percentComplete": 40.0,
            "lessons": [],
        }

        # Patch the progress controller to capture the call
        with patch.object(index_mod, "handle_progress_request") as mock_handle:
            mock_handle.return_value = {
                "statusCode": 200,
                "body": '{"courseId": "course-123", "completedCount": 2}',
                "headers": {"Content-Type": "application/json"},
            }

            monkeypatch.setattr(
                index_mod,
                "lambda_bootstrap",
                _bootstrap_returning(cfg_wildcard, mock_service, mock_auth, mock_progress),
            )

            evt = make_lambda_event(method="GET", path="/courses/course-123/progress")
            resp = index_mod.lambda_handler(evt, None)

            # Verify the progress controller was called
            mock_handle.assert_called_once()
            call_kwargs = mock_handle.call_args[1]
            assert call_kwargs["origin"] is not None
            assert call_kwargs["progress_svc"] is mock_progress

    def test_put_lesson_progress_routes_to_controller_when_rds_enabled(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        """When RDS is enabled, PUT /courses/{id}/lessons/{id}/progress should route to progress controller."""
        mock_service = MagicMock(spec=CourseManagementService)
        mock_auth = MagicMock()
        mock_progress = MagicMock()

        with patch.object(index_mod, "handle_progress_request") as mock_handle:
            mock_handle.return_value = {
                "statusCode": 200,
                "body": '{"ok": true, "lessonProgress": {"lessonId": "lesson-456", "completed": true}}',
                "headers": {"Content-Type": "application/json"},
            }

            monkeypatch.setattr(
                index_mod,
                "lambda_bootstrap",
                _bootstrap_returning(cfg_wildcard, mock_service, mock_auth, mock_progress),
            )

            evt = make_lambda_event(
                method="PUT",
                path="/courses/course-123/lessons/lesson-456/progress",
                body={"position": 60, "duration": 120},
            )
            resp = index_mod.lambda_handler(evt, None)

            assert resp["statusCode"] == 200
            mock_handle.assert_called_once()
            call_kwargs = mock_handle.call_args[1]
            assert call_kwargs["progress_svc"] is mock_progress

    def test_progress_options_preflight_returns_204(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        """OPTIONS requests to progress endpoints should return 204 preflight."""
        mock_service = MagicMock(spec=CourseManagementService)
        mock_auth = MagicMock()
        mock_progress = MagicMock()

        monkeypatch.setattr(
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, mock_service, mock_auth, mock_progress),
        )

        evt = make_lambda_event(
            method="OPTIONS",
            path="/courses/course-123/progress",
            headers={"origin": "http://localhost:5173"},
        )
        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 204

    def test_progress_endpoint_returns_503_when_catalog_unconfigured(
        self,
        monkeypatch: pytest.MonkeyPatch,
        cfg_wildcard: AppConfig,
        make_lambda_event,
    ) -> None:
        """Progress endpoints should return catalog_unconfigured 503 when RDS is not wired."""
        monkeypatch.setattr(
            index_mod,
            "lambda_bootstrap",
            _bootstrap_returning(cfg_wildcard, None, None, None),
        )
        evt = make_lambda_event(method="GET", path="/courses/course-123/progress")

        resp = index_mod.lambda_handler(evt, None)

        assert resp["statusCode"] == 503
        body = json.loads(resp["body"])
        assert body["code"] == "catalog_unconfigured"
