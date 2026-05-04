"""Tests for services/common/runtime_context.py - Contextvar management.

TDD Phase: RED - Write failing tests first.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

import pytest


class TestBindRequestContext:
    """Test Case: test_bind_request_context_sets_contextvars

    After bind, get_request_context() returns dict with expected keys.
    """

    def test_bind_request_context_sets_contextvars(self):
        """Binding sets context variables correctly."""
        from services.common import runtime_context

        runtime_context.bind_request_context(
            lambda_request_id="lambda-abc-123",
            api_request_id="api-def-456",
            http_method="POST",
            route_or_action="create_course",
        )

        try:
            ctx = runtime_context.get_request_context()
            assert ctx["lambda_request_id"] == "lambda-abc-123"
            assert ctx["api_request_id"] == "api-def-456"
            assert ctx["http_method"] == "POST"
            assert ctx["route_or_action"] == "create_course"
        finally:
            runtime_context.clear_request_context()

    def test_bind_request_context_with_partial_values(self):
        """Binding with only some values sets defaults for others."""
        from services.common import runtime_context

        runtime_context.bind_request_context(
            lambda_request_id="lambda-only",
        )

        try:
            ctx = runtime_context.get_request_context()
            assert ctx["lambda_request_id"] == "lambda-only"
            # Other fields should have sensible defaults (None or empty)
            assert "api_request_id" in ctx
        finally:
            runtime_context.clear_request_context()


class TestClearRequestContext:
    """Test Case: test_clear_request_context_cleans_up

    After clear, get_request_context() returns empty/default state.
    """

    def test_clear_request_context_cleans_up(self):
        """Clearing removes context variables."""
        from services.common import runtime_context

        # First bind some context
        runtime_context.bind_request_context(
            lambda_request_id="lambda-abc-123",
            api_request_id="api-def-456",
        )

        # Verify it's set
        ctx = runtime_context.get_request_context()
        assert ctx["lambda_request_id"] == "lambda-abc-123"

        # Now clear
        runtime_context.clear_request_context()

        # Should return empty/default
        ctx = runtime_context.get_request_context()
        assert ctx == {} or ctx.get("lambda_request_id") is None


class TestExtractRestApiRequestId:
    """Test Case: test_extract_rest_api_request_id

    REST API GW event shape → extracts requestContext.requestId.
    """

    def test_extract_rest_api_request_id(self):
        """Extracts requestId from REST API Gateway event."""
        from services.common import runtime_context

        event: Dict[str, Any] = {
            "requestContext": {
                "requestId": "rest-api-request-123",
                "http": {"method": "GET"},
            },
            "rawPath": "/courses",
        }

        request_id = runtime_context.extract_api_request_id(event)
        assert request_id == "rest-api-request-123"


class TestExtractHttpApiRequestId:
    """Test Case: test_extract_http_api_request_id

    HTTP API GW event shape → extracts requestContext.http.requestId.
    """

    def test_extract_http_api_request_id(self):
        """Extracts requestId from HTTP API Gateway event."""
        from services.common import runtime_context

        event: Dict[str, Any] = {
            "requestContext": {
                "http": {
                    "requestId": "http-api-request-456",
                    "method": "POST",
                }
            },
            "rawPath": "/courses",
        }

        request_id = runtime_context.extract_api_request_id(event)
        assert request_id == "http-api-request-456"


class TestContextIsolation:
    """Test Case: test_context_isolation_across_calls

    Contextvars properly isolated (simulated concurrent requests don't leak).
    """

    def test_context_isolation_simulated(self):
        """Context from one request doesn't leak to another."""
        from services.common import runtime_context

        # Simulate Request 1
        runtime_context.bind_request_context(
            lambda_request_id="request-1",
            api_request_id="api-1",
        )

        ctx1 = runtime_context.get_request_context()
        assert ctx1["lambda_request_id"] == "request-1"

        # Clear Request 1 context
        runtime_context.clear_request_context()

        # Simulate Request 2
        runtime_context.bind_request_context(
            lambda_request_id="request-2",
            api_request_id="api-2",
        )

        ctx2 = runtime_context.get_request_context()
        assert ctx2["lambda_request_id"] == "request-2"

        # Request 1's context should not be visible
        assert ctx1["lambda_request_id"] != ctx2["lambda_request_id"]

        runtime_context.clear_request_context()


class TestExtractFromLambdaContext:
    """Test extraction of Lambda context values."""

    def test_extract_lambda_request_id(self):
        """Extract aws_request_id from Lambda context."""
        from services.common import runtime_context

        class MockLambdaContext:
            aws_request_id = "lambda-context-123"
            function_name = "test-function"

        ctx = MockLambdaContext()
        request_id = runtime_context.extract_lambda_request_id(ctx)
        assert request_id == "lambda-context-123"

    def test_extract_lambda_request_id_missing(self):
        """Handle missing aws_request_id gracefully."""
        from services.common import runtime_context

        class MockLambdaContext:
            function_name = "test-function"

        ctx = MockLambdaContext()
        request_id = runtime_context.extract_lambda_request_id(ctx)
        assert request_id is None or request_id == ""


class TestHelperFunctions:
    """Test helper functions for common patterns."""

    def test_bind_from_lambda_event_and_context(self):
        """High-level helper that binds from both Lambda and API GW sources."""
        from services.common import runtime_context

        class MockLambdaContext:
            aws_request_id = "lambda-ctx-789"

        event: Dict[str, Any] = {
            "requestContext": {
                "requestId": "api-gw-abc",
                "http": {"method": "PUT"},
            },
            "rawPath": "/courses/course-123",
        }

        runtime_context.bind_from_lambda_event(
            event=event,
            lambda_context=MockLambdaContext(),
            route_or_action="update_course",
        )

        try:
            ctx = runtime_context.get_request_context()
            assert ctx["lambda_request_id"] == "lambda-ctx-789"
            assert ctx["api_request_id"] == "api-gw-abc"
            assert ctx["http_method"] == "PUT"
            assert ctx["route_or_action"] == "update_course"
        finally:
            runtime_context.clear_request_context()

    def test_update_action_in_context(self):
        """Can update just the action field after routing."""
        from services.common import runtime_context

        runtime_context.bind_request_context(
            lambda_request_id="lambda-123",
            route_or_action="unknown",
        )

        try:
            # After routing, update the action
            runtime_context.update_action("get_course")

            ctx = runtime_context.get_request_context()
            assert ctx["route_or_action"] == "get_course"
            assert ctx["lambda_request_id"] == "lambda-123"  # Preserved
        finally:
            runtime_context.clear_request_context()


class TestEdgeCases:
    """Edge case handling."""

    def test_empty_event(self):
        """Handle empty event gracefully."""
        from services.common import runtime_context

        request_id = runtime_context.extract_api_request_id({})
        assert request_id is None or request_id == ""

    def test_missing_request_context(self):
        """Handle event without requestContext."""
        from services.common import runtime_context

        event: Dict[str, Any] = {"rawPath": "/courses"}
        request_id = runtime_context.extract_api_request_id(event)
        assert request_id is None or request_id == ""

    def test_none_lambda_context(self):
        """Handle None Lambda context."""
        from services.common import runtime_context

        request_id = runtime_context.extract_lambda_request_id(None)
        assert request_id is None or request_id == ""
