"""Unit tests for question-bank MCQ validation helpers."""

from __future__ import annotations

import pytest

from services.common.errors import BadRequest
from services.question_banks.mcq_validation import (
    extract_option_keys,
    validate_correct_option_key,
    validate_draft_question_for_publish,
    validate_mcq_options_json,
)


def test_extract_option_keys_from_array() -> None:
    keys = extract_option_keys(
        [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}]
    )
    assert keys == {"A", "B"}


def test_extract_option_keys_from_json_string() -> None:
    keys = extract_option_keys('[{"key": "A", "text": "a"}]')
    assert keys == {"A"}


def test_validate_mcq_options_json_rejects_empty() -> None:
    with pytest.raises(BadRequest, match="optionsJson"):
        validate_mcq_options_json([])


def test_validate_correct_option_key_rejects_unknown_key() -> None:
    with pytest.raises(BadRequest, match="correctOptionKey"):
        validate_correct_option_key(
            "Z", options_json=[{"key": "A", "text": "a"}]
        )


def test_validate_draft_question_for_publish_happy_path() -> None:
    validate_draft_question_for_publish(
        correct_option_key="A",
        options_json=[{"key": "A", "text": "a"}],
    )
