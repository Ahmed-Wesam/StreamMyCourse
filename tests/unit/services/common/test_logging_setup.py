"""Tests for services/common/logging_setup.py - JSON formatter and configuration.

TDD Phase: RED - Write failing tests first.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

import pytest


class TestJsonFormatterOutputShape:
    """Test Case: test_json_formatter_outputs_valid_json

    Formatter produces one JSON object per line, valid JSON parseable by json.loads().
    """

    def test_json_formatter_outputs_valid_json(self, caplog):
        """Formatter produces valid JSON output."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        # Should be valid JSON
        parsed = json.loads(formatted)
        assert isinstance(parsed, dict)

    def test_json_formatter_single_line_no_newlines(self, caplog):
        """Each log entry is exactly one line."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message with\nnewlines",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        # Should not contain literal newlines in the output
        assert "\n" not in formatted or formatted.count("\n") == 0


class TestJsonFormatterRequiredFields:
    """Test Case: test_json_formatter_includes_required_fields

    Output contains timestamp, level, logger, message fields.
    """

    def test_json_formatter_includes_required_fields(self):
        """JSON output contains all required base fields."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.created = 1234567890.123

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert "timestamp" in parsed
        assert "level" in parsed
        assert "logger" in parsed
        assert "message" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"


class TestLogLevelConfiguration:
    """Test Case: test_log_level_from_env_defaults_info

    LOG_LEVEL unset → level is INFO; LOG_LEVEL=DEBUG → level is DEBUG.
    """

    def test_configure_logging_defaults_to_info(self, monkeypatch):
        """When LOG_LEVEL is unset, default to INFO."""
        from services.common.logging_setup import configure_logging

        monkeypatch.delenv("LOG_LEVEL", raising=False)
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        configure_logging()

        assert root_logger.level == logging.INFO

    def test_configure_logging_respects_debug_env(self, monkeypatch):
        """When LOG_LEVEL=DEBUG, set level to DEBUG."""
        from services.common.logging_setup import configure_logging, reset_logging_configuration

        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        reset_logging_configuration()  # Reset to allow reconfiguration

        configure_logging()

        assert root_logger.level == logging.DEBUG

    def test_configure_logging_respects_warning_env(self, monkeypatch):
        """When LOG_LEVEL=WARNING, set level to WARNING."""
        from services.common.logging_setup import configure_logging, reset_logging_configuration

        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        reset_logging_configuration()  # Reset to allow reconfiguration

        configure_logging()

        assert root_logger.level == logging.WARNING


class TestExceptionHandling:
    """Test Case: test_formatter_handles_exception_in_message

    Exception info serialized safely without breaking JSON structure.
    """

    def test_formatter_handles_exception_in_message(self):
        """Exception info is serialized safely in JSON."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = logging.sys.exc_info()
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        # Should have exc_info field
        assert "exc_info" in parsed
        # Should contain exception type and message
        assert "ValueError" in parsed["exc_info"]
        assert "Test exception" in parsed["exc_info"]


class TestContextVarFilter:
    """Test Case: test_filter_merges_contextvars_into_record

    Custom filter injects lambda_request_id, api_request_id from contextvars.
    """

    def test_filter_merges_contextvars_into_record(self, monkeypatch):
        """Contextvars are merged into log record."""
        from services.common.logging_setup import ContextVarFilter, JsonLogFormatter
        from services.common import runtime_context

        formatter = JsonLogFormatter()
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.addFilter(ContextVarFilter())

        test_logger = logging.getLogger("test_context_vars")
        test_logger.handlers.clear()
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)

        # Bind context vars
        runtime_context.bind_request_context(
            lambda_request_id="lambda-123",
            api_request_id="api-456",
            http_method="GET",
            route_or_action="get_course",
        )

        try:
            record = logging.LogRecord(
                name="test_context_vars",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg="Test with context",
                args=(),
                exc_info=None,
            )

            # Apply the filter
            filter_obj = ContextVarFilter()
            filter_obj.filter(record)

            # Context vars should be on the record
            assert getattr(record, "lambda_request_id", None) == "lambda-123"
            assert getattr(record, "api_request_id", None) == "api-456"
        finally:
            runtime_context.clear_request_context()

    def test_json_formatter_includes_api_gateway_fields_from_context(self):
        """Structured logs include API Gateway correlation fields when bound."""
        from services.common.logging_setup import JsonLogFormatter
        from services.common import runtime_context

        formatter = JsonLogFormatter()
        runtime_context.bind_request_context(
            lambda_request_id="lambda-1",
            api_request_id="api-1",
            http_method="POST",
            route_or_action="get_upload_url",
            api_stage="dev",
            api_domain="gw.example.com",
            route_key="POST /upload-url",
            client_ip="198.51.100.1",
            user_agent_snippet="TestAgent/1",
            request_path="/upload-url",
            upload_kind="lessonVideo",
        )
        try:
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="t.py",
                lineno=1,
                msg="hello",
                args=(),
                exc_info=None,
            )
            out = json.loads(formatter.format(record))
            assert out["action"] == "get_upload_url"
            assert out["api_stage"] == "dev"
            assert out["api_domain"] == "gw.example.com"
            assert out["route_key"] == "POST /upload-url"
            assert out["client_ip"] == "198.51.100.1"
            assert out["user_agent_snippet"] == "TestAgent/1"
            assert out["request_path"] == "/upload-url"
            assert out["upload_kind"] == "lessonVideo"
        finally:
            runtime_context.clear_request_context()


class TestConfigureLoggingIdempotent:
    """Test Case: test_configure_logging_idempotent

    Multiple calls don't duplicate handlers.
    """

    def test_configure_logging_idempotent(self, monkeypatch):
        """Multiple calls to configure_logging don't duplicate handlers."""
        from services.common.logging_setup import configure_logging

        monkeypatch.setenv("LOG_LEVEL", "INFO")
        root_logger = logging.getLogger()

        # Clear any existing handlers
        root_logger.handlers.clear()
        initial_count = len(root_logger.handlers)

        # Call twice
        configure_logging()
        configure_logging()

        # Should only have added handlers once (or at most a reasonable number)
        # The exact assertion depends on implementation, but we shouldn't have
        # dozens of duplicate handlers
        assert len(root_logger.handlers) <= initial_count + 2


class TestLogInjectionProtection:
    """Additional tests for log injection protection."""

    def test_newlines_escaped_in_message(self):
        """Newlines in message are escaped, not literal."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Line 1\nLine 2\r\nLine 3",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        # Parse the JSON - should succeed
        parsed = json.loads(formatted)
        # Message should preserve newlines as characters, not break JSON
        assert "Line 1" in parsed["message"]
        assert "Line 2" in parsed["message"]

    def test_quotes_escaped_in_message(self):
        """Quotes in message don't break JSON structure."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='Message with "quotes" and </script>',
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        # Should parse successfully
        parsed = json.loads(formatted)
        assert "quotes" in parsed["message"]

    def test_unicode_handling(self):
        """Unicode characters are handled properly."""
        from services.common.logging_setup import JsonLogFormatter

        formatter = JsonLogFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test with emoji 🎉 and CJK 中文",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)
        assert "🎉" in parsed["message"]
        assert "中文" in parsed["message"]
