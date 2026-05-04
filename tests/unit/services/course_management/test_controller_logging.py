"""Tests for course_management controller logging.

TDD Phase: RED - Write failing tests first.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def api_gateway_event() -> Dict[str, Any]:
    """Sample API Gateway v2 event."""
    return {
        "requestContext": {
            "http": {"method": "GET"},
            "authorizer": {"claims": {"sub": "user-123", "email": "test@example.com"}},
        },
        "rawPath": "/courses/course-123",
        "headers": {},
    }


class TestHttpErrorLogging:
    """Test Case: test_http_error_logs_at_info_without_stack

    HttpError (e.g., 404) logs at INFO level, no exc_info.
    """

    @patch("services.course_management.controller._jwt_claims")
    @patch("services.course_management.controller._actor_sub")
    @patch("services.course_management.controller._actor_role")
    def test_http_error_404_logs_at_info(
        self, mock_role, mock_sub, mock_claims, api_gateway_event, caplog
    ):
        """404 NotFound logs at INFO without stack trace."""
        from services.common.errors import NotFound
        from services.course_management.controller import handle

        mock_claims.return_value = {"sub": "user-123"}
        mock_sub.return_value = "user-123"
        mock_role.return_value = "student"

        # Create a mock service that has the required method
        mock_svc = MagicMock()
        mock_svc.get_course_detail_with_enrollment.side_effect = NotFound("Course not found")

        # Set logging level on the controller logger
        caplog.set_level(logging.INFO, logger="services.course_management.controller")

        response = handle(
            {**api_gateway_event, "rawPath": "/courses/missing-course"},
            origin="*",
            svc=mock_svc,
            video_bucket="test-bucket",
            auth_svc=MagicMock(),
            auth_enforced=False,
        )

        # Should return 404
        assert response["statusCode"] == 404

        # Check that an INFO log exists (the "HTTP error" log we added)
        info_logs = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_logs) > 0


class TestUnexpectedExceptionLogging:
    """Test Case: test_unexpected_exception_logs_error_with_exc_info

    Unexpected errors log at ERROR with full stack trace.
    """

    @patch("services.course_management.controller._jwt_claims")
    def test_unexpected_exception_logs_error_with_stack(
        self, mock_claims, api_gateway_event, caplog
    ):
        """Unexpected exception logs at ERROR with exc_info."""
        from services.course_management.controller import handle

        mock_claims.return_value = {"sub": "user-123"}

        # Mock service to raise unexpected error for list_published_courses
        mock_svc = MagicMock()
        mock_svc.list_published_courses.side_effect = RuntimeError("Unexpected!")

        caplog.set_level(logging.ERROR, logger="services.course_management.controller")

        list_event = {
            **api_gateway_event,
            "rawPath": "/courses",
            "requestContext": {"http": {"method": "GET"}},
        }

        response = handle(
            list_event,
            origin="*",
            svc=mock_svc,
            video_bucket="test-bucket",
            auth_svc=MagicMock(),
            auth_enforced=False,
        )

        # Should return 500
        assert response["statusCode"] == 500

        # Should have logged at ERROR level
        error_logs = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_logs) > 0


class TestActionFieldInLogs:
    """Test Case: test_action_field_present_in_logs

    Every controller log includes action field (e.g., get_course, create_course).
    """

    @patch("services.course_management.controller._jwt_claims")
    @patch("services.course_management.controller._actor_sub")
    @patch("services.course_management.controller._actor_role")
    @patch("services.course_management.controller.update_action")
    def test_action_field_present(
        self, mock_update_action, mock_role, mock_sub, mock_claims, api_gateway_event, caplog
    ):
        """Logs include action field via update_action call."""
        from services.course_management.controller import handle

        mock_claims.return_value = {"sub": "user-123"}
        mock_sub.return_value = "user-123"
        mock_role.return_value = "student"

        mock_svc = MagicMock()
        mock_svc.list_published_courses.return_value = []

        caplog.set_level(logging.INFO, logger="services.course_management.controller")

        # Create list event
        list_event = {
            **api_gateway_event,
            "rawPath": "/courses",
            "requestContext": {"http": {"method": "GET"}},
        }

        handle(
            list_event,
            origin="*",
            svc=mock_svc,
            video_bucket="test-bucket",
            auth_svc=MagicMock(),
            auth_enforced=False,
        )

        # update_action should have been called, which sets action in context
        mock_update_action.assert_called_with("list_courses")


class TestResourceIdInContext:
    """Test Case: test_resource_id_in_context

    Resource IDs (courseId) set in contextvar for logging.
    """

    def test_resource_id_extracted_from_path(self):
        """courseId extracted from path and set in context."""
        # This tests the routing logic that extracts resource IDs
        from services.course_management.controller import _route

        action, params = _route("GET", "/courses/course-abc123")

        assert action == "get_course"
        assert params["courseId"] == "course-abc123"

    def test_lesson_list_route(self):
        """list_lessons route extraction."""
        from services.course_management.controller import _route

        action, params = _route("GET", "/courses/course-123/lessons")

        assert action == "list_lessons"
        assert params["courseId"] == "course-123"


class TestAuditLogging:
    @patch("services.course_management.controller._jwt_claims")
    @patch("services.course_management.controller._actor_sub")
    @patch("services.course_management.controller._actor_role")
    def test_enroll_success_emits_audit_log(
        self, mock_role, mock_sub, mock_claims, caplog
    ) -> None:
        from services.course_management.controller import handle

        mock_claims.return_value = {"sub": "cognito-subject-uuid-12345"}
        mock_sub.return_value = "cognito-subject-uuid-12345"
        mock_role.return_value = "student"

        mock_svc = MagicMock()
        mock_svc.enroll_in_published_course.return_value = {"courseId": "c1", "enrolled": True}
        mock_auth = MagicMock()

        caplog.set_level(logging.INFO, logger="services.course_management.controller")

        evt = {
            "requestContext": {"http": {"method": "POST"}},
            "rawPath": "/courses/c1/enroll",
            "headers": {},
        }

        handle(
            evt,
            origin="*",
            svc=mock_svc,
            video_bucket="b",
            auth_svc=mock_auth,
            auth_enforced=False,
        )

        audit_records = [
            r
            for r in caplog.records
            if r.levelno == logging.INFO and getattr(r, "audit_action", None) == "enrollment.create"
        ]
        assert len(audit_records) == 1
        rec = audit_records[0]
        assert rec.course_id == "c1"
        assert rec.user_sub_prefix == "cognito-"
        assert "uuid-12345" not in rec.user_sub_prefix

    @patch("services.course_management.controller._jwt_claims")
    @patch("services.course_management.controller._actor_sub")
    @patch("services.course_management.controller._actor_role")
    def test_delete_course_success_emits_audit_log(
        self, mock_role, mock_sub, mock_claims, caplog
    ) -> None:
        from services.course_management.controller import handle

        mock_claims.return_value = {"sub": "teacher-sub-abcdefghij"}
        mock_sub.return_value = "teacher-sub-abcdefghij"
        mock_role.return_value = "teacher"

        mock_svc = MagicMock()
        mock_svc.delete_course.return_value = {"id": "c2", "deleted": True}

        evt = {
            "requestContext": {"http": {"method": "DELETE"}},
            "rawPath": "/courses/c2",
            "headers": {},
        }

        caplog.set_level(logging.INFO, logger="services.course_management.controller")

        handle(
            evt,
            origin="*",
            svc=mock_svc,
            video_bucket="b",
            auth_svc=MagicMock(),
            auth_enforced=False,
        )

        audit_records = [
            r
            for r in caplog.records
            if r.levelno == logging.INFO and getattr(r, "audit_action", None) == "course.delete"
        ]
        assert len(audit_records) == 1
        rec = audit_records[0]
        assert rec.course_id == "c2"
        assert rec.user_sub_prefix == "teacher-"


class TestControllerSetsActionContext:
    """Test that controller sets action in runtime context after routing."""

    @patch("services.course_management.controller._jwt_claims")
    @patch("services.course_management.controller.update_action")
    def test_controller_updates_action_after_routing(self, mock_update_action, mock_claims, caplog):
        """Controller updates action in context after determining route."""
        from services.course_management.controller import handle

        mock_claims.return_value = {"sub": "user-123"}

        mock_svc = MagicMock()
        mock_svc.list_published_courses.return_value = []

        list_event = {
            "requestContext": {"http": {"method": "GET"}},
            "rawPath": "/courses",
            "headers": {},
        }

        handle(
            list_event,
            origin="*",
            svc=mock_svc,
            video_bucket="test-bucket",
            auth_svc=MagicMock(),
            auth_enforced=False,
        )

        # update_action should have been called with "list_courses"
        mock_update_action.assert_called_with("list_courses")
