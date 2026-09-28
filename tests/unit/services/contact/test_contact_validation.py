"""Unit tests for contact form payload validation."""

from __future__ import annotations

import pytest

from services.common.errors import BadRequest
from services.contact.validation import (
    CONTACT_ALLOWED_KEYS,
    CONTACT_CATEGORIES,
    parse_contact_payload,
)


def _valid_body(**overrides: str) -> dict[str, str]:
    base = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "category": "General Question",
        "subject": "Hello",
        "message": "I have a question about your courses.",
    }
    base.update(overrides)
    return base


class TestUnknownFields:
    def test_rejects_unknown_top_level_keys(self) -> None:
        body = _valid_body(to="evil@example.com")
        with pytest.raises(BadRequest, match="Unknown field"):
            parse_contact_payload(body)

    def test_rejects_attachment_field(self) -> None:
        with pytest.raises(BadRequest, match="Unknown field"):
            parse_contact_payload(_valid_body(attachment="file.bin"))


class TestRequiredFields:
    @pytest.mark.parametrize("missing", ["name", "email", "category", "subject", "message"])
    def test_missing_required_field(self, missing: str) -> None:
        body = _valid_body()
        del body[missing]
        with pytest.raises(BadRequest):
            parse_contact_payload(body)

    def test_empty_string_required_field(self) -> None:
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(name="   "))


class TestFieldLimits:
    def test_name_max_length(self) -> None:
        parse_contact_payload(_valid_body(name="x" * 100))
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(name="x" * 101))

    def test_email_max_length(self) -> None:
        parse_contact_payload(_valid_body(email=("a" * 240) + "@example.com"))
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(email=("a" * 245) + "@example.com"))

    def test_subject_max_length(self) -> None:
        parse_contact_payload(_valid_body(subject="s" * 200))
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(subject="s" * 201))

    def test_message_max_length(self) -> None:
        parse_contact_payload(_valid_body(message="m" * 5000))
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(message="m" * 5001))


class TestForbiddenCharacters:
    @pytest.mark.parametrize("field", ["name", "email", "subject"])
    @pytest.mark.parametrize("bad", ["comma,here", "line\nbreak", "cr\rhere"])
    def test_rejects_comma_and_newlines(self, field: str, bad: str) -> None:
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(**{field: bad}))

    def test_message_allows_newlines(self) -> None:
        parsed = parse_contact_payload(_valid_body(message="Line one\nLine two"))
        assert "Line one" in parsed.message


class TestEmailShape:
    @pytest.mark.parametrize(
        "email",
        ["not-an-email", "@nodomain.com", "missingatsign.com", "spaces here@x.com"],
    )
    def test_invalid_email_shape(self, email: str) -> None:
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(email=email))

    def test_valid_email_accepted(self) -> None:
        parsed = parse_contact_payload(_valid_body(email="user.name+tag@example.org"))
        assert parsed.email == "user.name+tag@example.org"


class TestCategory:
    @pytest.mark.parametrize("category", CONTACT_CATEGORIES)
    def test_each_allowed_category(self, category: str) -> None:
        parsed = parse_contact_payload(_valid_body(category=category))
        assert parsed.category == category

    def test_unknown_category_rejected(self) -> None:
        with pytest.raises(BadRequest):
            parse_contact_payload(_valid_body(category="Random Category"))


class TestHoneypotField:
    def test_rs_hp_optional_empty(self) -> None:
        parsed = parse_contact_payload(_valid_body())
        assert parsed.honeypot == ""

    def test_rs_hp_parsed_when_present(self) -> None:
        parsed = parse_contact_payload(_valid_body(rs_hp="bot"))
        assert parsed.honeypot == "bot"

    def test_non_string_rs_hp_treated_as_honeypot(self) -> None:
        body = _valid_body()
        body["rs_hp"] = 1
        parsed = parse_contact_payload(body)
        assert parsed.honeypot == "non-string"


def test_allowed_keys_frozen_contract() -> None:
    assert CONTACT_ALLOWED_KEYS == frozenset(
        {"name", "email", "category", "subject", "message", "rs_hp"}
    )
