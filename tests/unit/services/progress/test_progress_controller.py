"""Unit tests for `services.progress.controller`.

Two slices:
1. `_route` — the router table; we drive it directly.
2. `handle_progress_request` — the dispatcher; we inject a `MagicMock` service to verify
   error mapping and JSON responses end-to-end.
"""

from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Forbidden, NotFound


# Import controller functions (may fail until implementation exists)
@pytest.fixture
def controller_module():
    """Import controller module, handling import errors during RED phase."""
    try:
        from services.progress import controller
        return controller
    except ImportError:
        pytest.skip("Controller module not yet implemented")


@pytest.fixture
def progress_svc() -> MagicMock:
    return MagicMock()


# --- _route table tests ------------------------------------------------------


class TestRouteTable:
    def test_get_course_progress_route(
        self, controller_module
    ) -> None:
        """GET /courses/{id}/progress → "get_course_progress"."""
        _route = controller_module._route
        action, params = _route("GET", "/courses/course-123/progress")
        assert action == "get_course_progress"
        assert params == {"courseId": "course-123"}

    def test_update_lesson_progress_route(
        self, controller_module
    ) -> None:
        """PUT /courses/{id}/lessons/{id}/progress → "update_lesson_progress"."""
        _route = controller_module._route
        action, params = _route("PUT", "/courses/course-123/lessons/lesson-456/progress")
        assert action == "update_lesson_progress"
        assert params == {"courseId": "course-123", "lessonId": "lesson-456"}

    def test_unknown_route_returns_not_found(
        self, controller_module
    ) -> None:
        """Unknown routes yield "not_found" action."""
        _route = controller_module._route
        action, params = _route("GET", "/unknown/path")
        assert action == "not_found"
        assert params == {}

    def test_wrong_method_on_progress_path(
        self, controller_module
    ) -> None:
        """POST on progress path is not found."""
        _route = controller_module._route
        action, params = _route("POST", "/courses/course-123/progress")
        assert action == "not_found"


# --- handle_progress_request tests -------------------------------------------


class TestHandleProgressRequest:
    def test_get_course_progress_success(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test successful get_course_progress request."""
        handle_progress_request = controller_module.handle_progress_request

        progress_svc.get_course_progress.return_value = {
            "courseId": "course-123",
            "totalReadyLessons": 3,
            "completedCount": 2,
            "percentComplete": 66.67,
            "lessons": [
                {"lessonId": "lesson-1", "completed": True, "lastPositionSec": 100},
                {"lessonId": "lesson-2", "completed": True, "lastPositionSec": 90},
                {"lessonId": "lesson-3", "completed": False, "lastPositionSec": 30},
            ],
        }

        evt = make_lambda_event(method="GET", path="/courses/course-123/progress")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["courseId"] == "course-123"
        assert body["totalReadyLessons"] == 3
        assert body["completedCount"] == 2
        progress_svc.get_course_progress.assert_called_once_with(
            user_sub="user-1", course_id="course-123", role="student"
        )

    def test_update_lesson_progress_success(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test successful update_lesson_progress request."""
        handle_progress_request = controller_module.handle_progress_request

        progress_svc.update_lesson_progress.return_value = {
            "ok": True,
            "lessonProgress": {
                "lessonId": "lesson-456",
                "completed": True,
                "lastPositionSec": 95,
                "completedAt": "2026-01-01T00:00:00Z",
            },
        }

        evt = make_lambda_event(
            method="PUT",
            path="/courses/course-123/lessons/lesson-456/progress",
            body={"position": 95, "duration": 100},
        )
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert body["ok"] is True
        assert body["lessonProgress"]["lessonId"] == "lesson-456"
        assert body["lessonProgress"]["completed"] is True

        progress_svc.update_lesson_progress.assert_called_once_with(
            user_sub="user-1",
            course_id="course-123",
            lesson_id="lesson-456",
            position=95,
            duration=100,
            mark_complete=False,
            mark_incomplete=False,
            role="student",
        )

    def test_update_with_mark_complete(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test update with explicit markComplete flag."""
        handle_progress_request = controller_module.handle_progress_request

        progress_svc.update_lesson_progress.return_value = {
            "ok": True,
            "lessonProgress": {"lessonId": "lesson-456", "completed": True, "lastPositionSec": 50},
        }

        evt = make_lambda_event(
            method="PUT",
            path="/courses/course-123/lessons/lesson-456/progress",
            body={"position": 50, "duration": 100, "markComplete": True},
        )
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 200
        call_kwargs = progress_svc.update_lesson_progress.call_args.kwargs
        assert call_kwargs["mark_complete"] is True

    def test_update_with_mark_incomplete(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test update with explicit markIncomplete flag."""
        handle_progress_request = controller_module.handle_progress_request

        progress_svc.update_lesson_progress.return_value = {
            "ok": True,
            "lessonProgress": {"lessonId": "lesson-456", "completed": False, "lastPositionSec": 100},
        }

        evt = make_lambda_event(
            method="PUT",
            path="/courses/course-123/lessons/lesson-456/progress",
            body={"position": 100, "duration": 100, "markIncomplete": True},
        )
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 200
        call_kwargs = progress_svc.update_lesson_progress.call_args.kwargs
        assert call_kwargs["mark_incomplete"] is True

    def test_forbidden_maps_to_403(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test that Forbidden error maps to 403 response."""
        handle_progress_request = controller_module.handle_progress_request

        progress_svc.get_course_progress.side_effect = Forbidden(
            "Subscription required", code="subscription_required"
        )

        evt = make_lambda_event(method="GET", path="/courses/course-123/progress")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 403
        body = json.loads(resp["body"])
        assert body["code"] == "subscription_required"
        assert "subscription" in body["message"].lower()

    def test_bad_request_maps_to_400(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test that BadRequest error maps to 400 response."""
        handle_progress_request = controller_module.handle_progress_request

        progress_svc.update_lesson_progress.side_effect = BadRequest(
            "Invalid position", code="invalid_position"
        )

        evt = make_lambda_event(
            method="PUT",
            path="/courses/course-123/lessons/lesson-456/progress",
            body={"position": 999, "duration": 100},
        )
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["code"] == "invalid_position"

    def test_not_found_route_returns_404(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test that unknown routes return 404."""
        handle_progress_request = controller_module.handle_progress_request

        evt = make_lambda_event(method="GET", path="/unknown/path")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 404
        body = json.loads(resp["body"])
        assert body["code"] == "not_found"

    def test_missing_position_body_field(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test that missing required body field returns 400."""
        handle_progress_request = controller_module.handle_progress_request

        evt = make_lambda_event(
            method="PUT",
            path="/courses/course-123/lessons/lesson-456/progress",
            body={"duration": 100},  # missing position
        )
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert "required" in body["message"].lower() or "position" in body["message"].lower()
        progress_svc.update_lesson_progress.assert_not_called()

    def test_options_request_returns_204(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test that OPTIONS request returns 204 with CORS headers."""
        handle_progress_request = controller_module.handle_progress_request

        evt = make_lambda_event(method="OPTIONS", path="/courses/course-123/progress")

        resp = handle_progress_request(
            evt,
            origin="https://app.example",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 204
        assert resp["headers"]["Access-Control-Allow-Origin"] == "https://app.example"
        progress_svc.assert_not_called()

    def test_unhandled_exception_returns_500(
        self, controller_module, progress_svc: MagicMock, make_lambda_event
    ) -> None:
        """Test that unhandled exceptions return 500."""
        handle_progress_request = controller_module.handle_progress_request

        progress_svc.get_course_progress.side_effect = RuntimeError("Unexpected error")

        evt = make_lambda_event(method="GET", path="/courses/course-123/progress")
        evt["requestContext"]["authorizer"] = {"claims": {"sub": "user-1"}}

        resp = handle_progress_request(
            evt,
            origin="*",
            progress_svc=progress_svc,
        )

        assert resp["statusCode"] == 500
        body = json.loads(resp["body"])
        assert body["code"] == "internal_error"
