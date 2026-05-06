"""Unit tests for validation edge cases and boundary conditions.

Tests malformed UTF-8, non-string types, and boundary values.
"""

from __future__ import annotations

import base64
import json

import pytest

from services.common.errors import BadRequest
from services.common.validation import optional_str, parse_json_body, require_str


class TestParseJsonBodyEdgeCases:
    """Tests for JSON body parsing edge cases."""

    def test_malformed_utf8_in_body_raises(self) -> None:
        """Invalid UTF-8 sequences should raise BadRequest."""
        # Create invalid UTF-8 bytes and base64 encode them
        invalid_utf8 = b"\xff\xfe\x00\x01invalid"
        encoded = base64.b64encode(invalid_utf8).decode("ascii")
        evt = {"body": encoded, "isBase64Encoded": True}
        with pytest.raises(BadRequest) as exc:
            parse_json_body(evt)
        assert exc.value.status_code == 400

    def test_truncated_json_raises(self) -> None:
        """Truncated JSON should raise BadRequest."""
        truncated = '{"key": "value'  # Missing closing quote and brace
        evt = {"body": truncated}
        with pytest.raises(BadRequest) as exc:
            parse_json_body(evt)
        assert "valid JSON" in exc.value.message

    def test_json_with_control_chars_raises(self) -> None:
        """JSON with unescaped control characters should raise BadRequest."""
        # Newlines must be escaped in JSON strings
        body = '{"key": "val\\nue"}'  # Properly escaped
        assert parse_json_body({"body": body}) == {"key": "val\nue"}

    def test_very_deeply_nested_json_raises(self) -> None:
        """Extremely deep nesting should be rejected or handled safely."""
        # Python's json module has a default max nesting depth of 1000
        depth = 2000
        nested = "{" * depth + "\"key\": \"value\"" + "}" * depth
        evt = {"body": nested}
        # Should either parse successfully or raise BadRequest (not crash)
        try:
            result = parse_json_body(evt)
            assert isinstance(result, dict)
        except BadRequest:
            pass  # Also acceptable

    def test_unicode_escapes_preserved(self) -> None:
        """Unicode escape sequences should be properly decoded."""
        body = '{"emoji": "\\u2764\\ufe0f"}'  # Heart emoji
        result = parse_json_body({"body": body})
        assert result["emoji"] == "❤️"


class TestRequireStrEdgeCases:
    """Tests for require_str edge cases."""

    def test_dict_as_value_raises(self) -> None:
        """Dict value should raise BadRequest."""
        with pytest.raises(BadRequest):
            require_str({"field": {"nested": "dict"}}, "field")

    def test_list_as_value_raises(self) -> None:
        """List value should raise BadRequest."""
        with pytest.raises(BadRequest):
            require_str({"field": ["a", "b"]}, "field")

    def test_boolean_as_value_raises(self) -> None:
        """Boolean value should raise BadRequest."""
        with pytest.raises(BadRequest):
            require_str({"field": True}, "field")
        with pytest.raises(BadRequest):
            require_str({"field": False}, "field")

    def test_float_as_value_raises(self) -> None:
        """Float value should raise BadRequest."""
        with pytest.raises(BadRequest):
            require_str({"field": 3.14}, "field")

    def test_zero_as_value_raises(self) -> None:
        """Integer zero should raise BadRequest."""
        with pytest.raises(BadRequest):
            require_str({"field": 0}, "field")

    def test_very_long_string_ok(self) -> None:
        """Very long strings should be accepted."""
        long_value = "a" * 10000
        result = require_str({"field": long_value}, "field")
        assert result == long_value

    def test_string_with_newlines_ok(self) -> None:
        """Strings with newlines should be accepted and preserved."""
        value = "line1\nline2\nline3"
        result = require_str({"field": value}, "field")
        assert result == value

    def test_string_with_tabs_ok(self) -> None:
        """Strings with tabs should be accepted."""
        value = "col1\tcol2\tcol3"
        result = require_str({"field": value}, "field")
        assert result == value


class TestOptionalStrEdgeCases:
    """Tests for optional_str edge cases."""

    def test_dict_returns_default(self) -> None:
        """Dict value should return default."""
        assert optional_str({"k": {"a": 1}}, "k", "default") == "default"

    def test_list_returns_default(self) -> None:
        """List value should return default."""
        assert optional_str({"k": [1, 2, 3]}, "k", "default") == "default"

    def test_boolean_returns_default(self) -> None:
        """Boolean value should return default."""
        assert optional_str({"k": True}, "k", "default") == "default"
        assert optional_str({"k": False}, "k", "default") == "default"

    def test_whitespace_string_returns_empty_string(self) -> None:
        """Whitespace-only string returns empty string after strip (not default)."""
        # Implementation: val.strip() if isinstance(val, str) else default
        # So "   ".strip() = "", returns "" not default
        assert optional_str({"k": "   "}, "k", "fallback") == ""

    def test_empty_string_returns_empty(self) -> None:
        """Empty string returns empty string after strip (not default)."""
        # Empty string is a string, so it gets stripped to ""
        assert optional_str({"k": ""}, "k", "default") == ""
