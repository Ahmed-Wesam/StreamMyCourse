"""Unit tests for playback watermark text derived from Cognito JWT claims."""

from __future__ import annotations

import pytest

from services.common.playback_watermark import (
    _cap_watermark,
    missing_watermark_profile_fields,
    playback_watermark_from_claims,
)


class TestMissingWatermarkProfileFields:
    def test_complete_profile(self) -> None:
        claims = {
            "given_name": "Jane",
            "family_name": "Doe",
            "email": "jane@gmail.com",
        }
        assert missing_watermark_profile_fields(claims) == ()

    def test_missing_name(self) -> None:
        assert missing_watermark_profile_fields({"email": "jane@gmail.com"}) == ("name",)

    def test_given_only_with_email_is_complete(self) -> None:
        assert missing_watermark_profile_fields(
            {"given_name": "Jane", "email": "jane@gmail.com"}
        ) == ()

    def test_family_only_with_email_is_complete(self) -> None:
        assert missing_watermark_profile_fields(
            {"family_name": "Doe", "email": "jane@gmail.com"}
        ) == ()

    def test_missing_email(self) -> None:
        assert missing_watermark_profile_fields(
            {"given_name": "Jane", "family_name": "Doe"}
        ) == ("email",)

    def test_missing_all(self) -> None:
        assert missing_watermark_profile_fields({}) == ("name", "email")


class TestPlaybackWatermarkFromClaims:
    def test_given_and_family_and_email(self) -> None:
        claims = {
            "given_name": "Jane",
            "family_name": "Doe",
            "email": "jane@gmail.com",
        }
        assert playback_watermark_from_claims(claims) == "Jane Doe\njane@gmail.com"

    def test_given_only_and_email(self) -> None:
        claims = {"given_name": "Jane", "email": "jane@gmail.com"}
        assert playback_watermark_from_claims(claims) == "Jane\njane@gmail.com"

    def test_family_only_and_email(self) -> None:
        claims = {"family_name": "Doe", "email": "jane@gmail.com"}
        assert playback_watermark_from_claims(claims) == "Doe\njane@gmail.com"

    def test_email_only_returns_none(self) -> None:
        assert playback_watermark_from_claims({"email": "jane@gmail.com"}) is None

    def test_empty_claims(self) -> None:
        assert playback_watermark_from_claims({}) is None

    def test_name_field_without_given_and_family_returns_none(self) -> None:
        claims = {"name": "Jane Doe", "email": "jane@gmail.com"}
        assert playback_watermark_from_claims(claims) is None

    def test_whitespace_collapse_on_given_and_family(self) -> None:
        claims = {
            "given_name": "  Jane   Marie  ",
            "family_name": "  Doe  ",
            "email": "jane@gmail.com",
        }
        assert playback_watermark_from_claims(claims) == "Jane Marie Doe\njane@gmail.com"

    def test_max_length_cap_preserves_full_email(self) -> None:
        long_given = "X" * 80
        long_family = "Y" * 50
        email = "user@example.com"
        claims = {
            "given_name": long_given,
            "family_name": long_family,
            "email": email,
        }
        name_line = f"{long_given} {long_family}"
        max_name_len = 120 - len(email) - 1
        expected = f"{name_line[:max_name_len]}\n{email}"
        assert playback_watermark_from_claims(claims) == expected
        assert email in playback_watermark_from_claims(claims)
        assert len(playback_watermark_from_claims(claims)) <= 120

    def test_max_length_cap_single_line(self) -> None:
        long_email = "a" * 130 + "@example.com"
        claims = {"given_name": "Jane", "family_name": "Doe", "email": long_email}
        result = playback_watermark_from_claims(claims)
        assert result is not None
        assert len(result) <= 120
        assert "\n" in result
        name_line, email_line = result.split("\n", 1)
        assert name_line.strip()
        assert email_line.strip()

    def test_max_length_cap_returns_none_when_name_cannot_fit(self) -> None:
        watermark = f"{'X' * 50}\n{'y' * 200}"
        assert _cap_watermark(watermark, 2) is None

    def test_empty_string_claims_are_ignored(self) -> None:
        claims = {
            "given_name": "",
            "family_name": "   ",
            "name": "Jane Doe",
            "email": "",
        }
        assert playback_watermark_from_claims(claims) is None

    def test_given_and_family_without_email_returns_none(self) -> None:
        claims = {"given_name": "Jane", "family_name": "Doe"}
        assert playback_watermark_from_claims(claims) is None
