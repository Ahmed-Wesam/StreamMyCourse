from __future__ import annotations

import base64
import json

import pytest

from services.common.errors import BadRequest
from services.common.validation import optional_str, parse_json_body, require_str


class TestRequireStr:
    def test_returns_stripped_value(self) -> None:
        assert require_str({"name": "  alice  "}, "name") == "alice"

    def test_missing_key_raises_bad_request(self) -> None:
        with pytest.raises(BadRequest) as exc:
            require_str({}, "name")
        assert "'name' is required" in exc.value.message
        assert exc.value.status_code == 400

    def test_empty_string_raises(self) -> None:
        with pytest.raises(BadRequest):
            require_str({"name": ""}, "name")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(BadRequest):
            require_str({"name": "   "}, "name")

    def test_non_string_raises(self) -> None:
        with pytest.raises(BadRequest):
            require_str({"name": 42}, "name")
        with pytest.raises(BadRequest):
            require_str({"name": None}, "name")
        with pytest.raises(BadRequest):
            require_str({"name": ["a"]}, "name")


class TestOptionalStr:
    def test_returns_stripped_value(self) -> None:
        assert optional_str({"k": "  hi  "}, "k") == "hi"

    def test_missing_returns_default_empty_string(self) -> None:
        assert optional_str({}, "k") == ""

    def test_missing_returns_explicit_default(self) -> None:
        assert optional_str({}, "k", "fallback") == "fallback"

    def test_non_string_returns_default(self) -> None:
        # Behavior chosen by the codebase: silently fall back for non-strings.
        # We pin it here so accidental "raise instead" refactors get caught.
        assert optional_str({"k": 42}, "k", "fallback") == "fallback"
        assert optional_str({"k": None}, "k", "fallback") == "fallback"
        assert optional_str({"k": ["a"]}, "k") == ""


class TestParseJsonBody:
    def test_dict_body_passthrough(self) -> None:
        body = {"a": 1}
        assert parse_json_body({"body": body}) is body

    def test_none_body_returns_empty_dict(self) -> None:
        assert parse_json_body({"body": None}) == {}
        assert parse_json_body({}) == {}

    def test_valid_json_string(self) -> None:
        evt = {"body": json.dumps({"hello": "world"})}
        assert parse_json_body(evt) == {"hello": "world"}

    def test_empty_string_body_treated_as_empty_object(self) -> None:
        # Source code substitutes `"{}"` for empty strings.
        assert parse_json_body({"body": ""}) == {}

    def test_valid_base64_encoded_json(self) -> None:
        encoded = base64.b64encode(json.dumps({"k": "v"}).encode("utf-8")).decode("ascii")
        evt = {"body": encoded, "isBase64Encoded": True}
        assert parse_json_body(evt) == {"k": "v"}

    def test_malformed_json_raises_bad_request(self) -> None:
        with pytest.raises(BadRequest) as exc:
            parse_json_body({"body": "{not json"})
        assert "valid JSON" in exc.value.message

    def test_non_object_json_list_raises(self) -> None:
        with pytest.raises(BadRequest) as exc:
            parse_json_body({"body": "[1, 2, 3]"})
        assert "JSON object" in exc.value.message

    def test_non_object_json_scalar_raises(self) -> None:
        with pytest.raises(BadRequest) as exc:
            parse_json_body({"body": "42"})
        assert "JSON object" in exc.value.message

    def test_malformed_base64_raises(self) -> None:
        # `!!!` is not valid base64 — but Python's b64decode is lenient about
        # padding/garbage, so use a payload that's both invalid b64 *and*
        # would not decode to UTF-8.
        evt = {"body": "@@@not-base64@@@", "isBase64Encoded": True}
        with pytest.raises(BadRequest) as exc:
            parse_json_body(evt)
        # Either "Invalid base64" (decode fails) or "valid JSON" (decode
        # produced gibberish that then failed json.loads) is acceptable —
        # both are 400s. Pin the status, not the precise message.
        assert exc.value.status_code == 400

    def test_non_string_non_dict_body_raises(self) -> None:
        with pytest.raises(BadRequest):
            parse_json_body({"body": 42})
        with pytest.raises(BadRequest):
            parse_json_body({"body": [1, 2]})

    def test_json_null_returns_empty_dict(self) -> None:
        # `null` is a valid JSON document but not an object; source treats it as {}.
        assert parse_json_body({"body": "null"}) == {}
