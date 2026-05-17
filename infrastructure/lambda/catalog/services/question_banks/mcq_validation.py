"""MCQ option/correct-answer validation for question banks (§9.1 / §9.3)."""

from __future__ import annotations

import json
from typing import Any, Set

from services.common.errors import BadRequest


def _parse_options_value(options_json: Any) -> Any:
    if isinstance(options_json, str):
        text = options_json.strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise BadRequest("optionsJson is not valid JSON") from exc
    return options_json


def _non_empty_option_keys_in_order(options_json: Any) -> list[str]:
    parsed = _parse_options_value(options_json)
    keys: list[str] = []
    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue
            raw = item.get("key")
            if isinstance(raw, str) and raw.strip():
                keys.append(raw.strip())
        return keys
    if isinstance(parsed, dict):
        for raw_key in parsed:
            key = str(raw_key).strip()
            if key:
                keys.append(key)
    return keys


def extract_option_keys(options_json: Any) -> Set[str]:
    """Return non-empty choice keys from ``optionsJson`` (array or object shape)."""
    return set(_non_empty_option_keys_in_order(options_json))


def validate_mcq_options_json(options_json: Any) -> None:
    """Require at least one choice with a non-empty key."""
    keys = _non_empty_option_keys_in_order(options_json)
    if not keys:
        raise BadRequest(
            "optionsJson must include at least one choice with a non-empty key"
        )
    if len(keys) != len(set(keys)):
        raise BadRequest("optionsJson must not contain duplicate option keys")


def validate_correct_option_key(
    correct_option_key: str | None, *, options_json: Any
) -> None:
    """When a correct key is present, it must match a choice key in ``optionsJson``."""
    key = (correct_option_key or "").strip()
    if not key:
        return
    option_keys = extract_option_keys(options_json)
    if key not in option_keys:
        raise BadRequest(
            "correctOptionKey must match a key in optionsJson"
        )


def validate_draft_question_for_publish(
    *,
    correct_option_key: str | None,
    options_json: Any,
) -> None:
    """Publish-time checks for one draft question row."""
    if not (correct_option_key or "").strip():
        raise BadRequest(
            "Cannot publish: every draft question must have a designated "
            "correct answer"
        )
    validate_mcq_options_json(options_json)
    validate_correct_option_key(correct_option_key, options_json=options_json)
