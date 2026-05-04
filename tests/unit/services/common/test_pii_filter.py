"""Tests for PII handling in logs.

NOTE: Per user requirement "log as is dont censor", we do NOT redact PII.
These tests verify that PII IS logged (not filtered) at all log levels.

TDD Phase: RED - Write failing tests first.
"""

from __future__ import annotations

import json
import logging

import pytest


class TestNoEmailRedaction:
    """Emails are NOT redacted - logged as-is per user requirement."""

    def test_email_logged_at_info_level(self, caplog):
        """Email addresses are logged as-is at INFO level."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User login: user@example.com",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # Email should be present as-is, NOT redacted
        assert "user@example.com" in parsed["message"]
        assert "[REDACTED_EMAIL]" not in parsed["message"]

    def test_email_in_extra_fields(self):
        """Email in extra fields is logged as-is."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="User action",
            args=(),
            exc_info=None,
        )
        # Add email as extra field
        record.user_email = "admin@company.com"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # Email should be present
        assert parsed.get("user_email") == "admin@company.com"


class TestNoJwtRedaction:
    """JWT tokens are NOT redacted - logged as-is per user requirement."""

    def test_jwt_logged_at_info_level(self, caplog):
        """Full JWT tokens are logged as-is at INFO level."""
        from services.common.logging_setup import JsonLogFormatter

        test_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Authorization: Bearer {test_jwt}",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # Full JWT should be present, NOT redacted
        assert test_jwt in parsed["message"]
        assert "[REDACTED_JWT]" not in parsed["message"]


class TestSubLoggedFully:
    """User sub claim logged fully (not just prefix)."""

    def test_full_sub_logged(self):
        """Full sub value is logged, not just prefix."""
        from services.common.logging_setup import JsonLogFormatter

        full_sub = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"User sub: {full_sub}",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # Full sub should be present
        assert full_sub in parsed["message"]
        # Should not have "sub|" prefix format
        assert "sub|" not in parsed["message"]


class TestRequestBodyLogged:
    """Request bodies logged at DEBUG level when enabled."""

    def test_request_body_logged_at_debug(self):
        """Full request body logged at DEBUG with LOG_DEBUG_BODY=true."""
        import os

        # Simulate DEBUG body logging enabled
        os.environ["LOG_DEBUG_BODY"] = "true"

        from services.common.logging_setup import JsonLogFormatter

        request_body = {"email": "user@test.com", "password": "secret123", "name": "John Doe"}

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=1,
            msg=f"Request body: {json.dumps(request_body)}",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # Full body including sensitive fields should be present
        assert "user@test.com" in parsed["message"]
        assert "secret123" in parsed["message"]
        assert "John Doe" in parsed["message"]

        del os.environ["LOG_DEBUG_BODY"]


class TestAuthorizationHeaderLogged:
    """Authorization header value logged as-is."""

    def test_full_authorization_header_logged(self):
        """Full Authorization header with bearer token logged as-is."""
        from services.common.logging_setup import JsonLogFormatter

        token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.payload.signature"

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Authorization header: {token}",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # Full token should be present, NOT "[REDACTED]"
        assert token in parsed["message"]
        assert "[REDACTED]" not in parsed["message"]
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" in parsed["message"]


class TestAllLevelsNoFiltering:
    """Verify NO filtering at any log level."""

    @pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR])
    def test_pii_logged_at_all_levels(self, level):
        """PII is logged as-is at all log levels."""
        from services.common.logging_setup import JsonLogFormatter

        test_message = "User: admin@example.com, Token: eyJ.test, Password: secret123"

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=level,
            pathname="test.py",
            lineno=1,
            msg=test_message,
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # All values should be present as-is
        assert "admin@example.com" in parsed["message"]
        assert "eyJ.test" in parsed["message"]
        assert "secret123" in parsed["message"]
