"""Presentation shuffle for module quiz attempts (§8.4)."""

from __future__ import annotations

import json
import random
from typing import Any

from services.question_banks.models import BoundQuestion


def shuffle_question_order(question_ids: list[str], rng: random.Random) -> list[str]:
    ordered = list(question_ids)
    rng.shuffle(ordered)
    return ordered


def shuffle_choice_orders_for_questions(
    questions: list[BoundQuestion],
    rng: random.Random,
) -> dict[str, list[str]]:
    orders: dict[str, list[str]] = {}
    for question in questions:
        keys = _option_keys_in_order(question.optionsJson)
        if not keys:
            raise ValueError(
                "optionsJson must include at least one choice with a non-empty key"
            )
        shuffled = list(keys)
        rng.shuffle(shuffled)
        orders[question.id] = shuffled
    return orders


def validate_question_order(
    question_ids: list[str], question_order: list[str]
) -> None:
    expected = set(question_ids)
    if set(question_order) != expected:
        unknown = sorted(set(question_order) - expected)
        if unknown:
            raise ValueError(
                f"question order contains unknown question id(s): {', '.join(unknown)}"
            )
        raise ValueError("question order is not a permutation of bound question ids")
    if len(question_order) != len(question_ids):
        raise ValueError("question order is not a permutation of bound question ids")


def validate_choice_order(options_json: Any, key_order: list[str]) -> None:
    expected = _option_keys_in_order(options_json)
    if not expected:
        raise ValueError(
            "optionsJson must include at least one choice with a non-empty key"
        )
    _assert_key_permutation(expected, key_order, label="choice order")


def apply_presentation_shuffle(
    questions: list[BoundQuestion],
    *,
    question_order: list[str],
    choice_orders: dict[str, list[str]],
) -> list[dict[str, Any]]:
    by_id = {question.id: question for question in questions}
    bound_ids = list(by_id)
    validate_question_order(bound_ids, question_order)
    result: list[dict[str, Any]] = []
    for question_id in question_order:
        question = by_id[question_id]
        key_order = choice_orders.get(question_id)
        if key_order is None:
            raise ValueError(
                f"choice order missing for question id {question_id}"
            )
        validate_choice_order(question.optionsJson, key_order)
        result.append(
            {
                "id": question.id,
                "promptText": question.promptText,
                "optionsJson": _reorder_options_by_keys(
                    question.optionsJson, key_order
                ),
            }
        )
    return result


def _parse_options_json(raw: Any) -> Any:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("optionsJson is not valid JSON") from exc
    return raw


def _option_keys_in_order(options_json: Any) -> list[str]:
    parsed = _parse_options_json(options_json)
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


def _reorder_options_by_keys(options_json: Any, key_order: list[str]) -> list[dict[str, str]]:
    parsed = _parse_options_json(options_json)
    text_by_key: dict[str, str] = {}
    if isinstance(parsed, list):
        for item in parsed:
            if not isinstance(item, dict):
                continue
            raw_key = item.get("key")
            if not isinstance(raw_key, str) or not raw_key.strip():
                continue
            key = raw_key.strip()
            text = item.get("text")
            text_by_key[key] = text if isinstance(text, str) else str(text or "")
    elif isinstance(parsed, dict):
        for raw_key, raw_text in parsed.items():
            key = str(raw_key).strip()
            if not key:
                continue
            text_by_key[key] = (
                raw_text if isinstance(raw_text, str) else str(raw_text or "")
            )
    validate_choice_order(options_json, key_order)
    return [{"key": key, "text": text_by_key[key]} for key in key_order]


def _assert_key_permutation(
    expected: list[str], key_order: list[str], *, label: str
) -> None:
    if len(key_order) != len(set(key_order)):
        raise ValueError(f"{label} is not a permutation of option keys")
    expected_set = set(expected)
    if set(key_order) != expected_set:
        unknown = sorted(set(key_order) - expected_set)
        if unknown:
            raise ValueError(
                f"{label} contains unknown option key(s): {', '.join(unknown)}"
            )
        raise ValueError(f"{label} is not a permutation of option keys")
