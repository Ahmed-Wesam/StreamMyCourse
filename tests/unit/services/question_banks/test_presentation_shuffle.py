"""Unit tests for module-quiz presentation shuffle (QB-G slice 2)."""

from __future__ import annotations

import json
import random

import pytest

from services.question_banks.models import BoundQuestion
from services.question_banks.presentation_shuffle import (
    apply_presentation_shuffle,
    shuffle_choice_orders_for_questions,
    shuffle_question_order,
    validate_choice_order,
    validate_question_order,
)

_QUESTION_IDS = ["q1", "q2", "q3", "q4"]

_Q1 = BoundQuestion(
    id="q1",
    promptText="First?",
    optionsJson=json.dumps(
        [
            {"key": "A", "text": "alpha"},
            {"key": "B", "text": "bravo"},
            {"key": "C", "text": "charlie"},
        ]
    ),
)
_Q2 = BoundQuestion(
    id="q2",
    promptText="Second?",
    optionsJson=json.dumps(
        [
            {"key": "X", "text": "ex"},
            {"key": "Y", "text": "why"},
        ]
    ),
)


def test_shuffle_question_order_fixed_rng_returns_permutation() -> None:
    rng = random.Random(42)
    shuffled = shuffle_question_order(_QUESTION_IDS, rng)
    assert shuffled == ["q3", "q2", "q4", "q1"]
    assert set(shuffled) == set(_QUESTION_IDS)
    assert len(shuffled) == len(_QUESTION_IDS)


def test_shuffle_question_order_empty_list() -> None:
    rng = random.Random(42)
    assert shuffle_question_order([], rng) == []


def test_shuffle_question_order_does_not_mutate_input() -> None:
    ids = ["q1", "q2"]
    original = list(ids)
    rng = random.Random(0)
    shuffle_question_order(ids, rng)
    assert ids == original


def test_shuffle_choice_orders_for_questions_fixed_rng() -> None:
    rng = random.Random(42)
    orders = shuffle_choice_orders_for_questions([_Q1, _Q2], rng)
    assert orders == {
        "q1": ["B", "A", "C"],
        "q2": ["Y", "X"],
    }


def test_shuffle_choice_orders_raises_when_no_option_keys() -> None:
    empty = BoundQuestion(id="q0", promptText="?", optionsJson="[]")
    rng = random.Random(42)
    with pytest.raises(ValueError, match="at least one"):
        shuffle_choice_orders_for_questions([empty], rng)


def test_validate_choice_order_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="unknown"):
        validate_choice_order(_Q1.optionsJson, ["A", "Z"])


def test_validate_choice_order_rejects_duplicate_key() -> None:
    with pytest.raises(ValueError, match="permutation"):
        validate_choice_order(_Q1.optionsJson, ["A", "A", "C"])


def test_validate_choice_order_rejects_incomplete_permutation() -> None:
    with pytest.raises(ValueError, match="permutation"):
        validate_choice_order(_Q1.optionsJson, ["A", "B"])


def test_validate_question_order_rejects_unknown_id() -> None:
    with pytest.raises(ValueError, match="unknown"):
        validate_question_order(["q1", "q2"], ["q1", "q9"])


def test_apply_presentation_shuffle_reorders_questions_and_options() -> None:
    question_order = ["q2", "q1"]
    choice_orders = {
        "q1": ["C", "A", "B"],
        "q2": ["Y", "X"],
    }
    result = apply_presentation_shuffle(
        [_Q1, _Q2],
        question_order=question_order,
        choice_orders=choice_orders,
    )
    assert [q["id"] for q in result] == ["q2", "q1"]
    assert result[0]["promptText"] == "Second?"
    assert result[0]["optionsJson"] == [
        {"key": "Y", "text": "why"},
        {"key": "X", "text": "ex"},
    ]
    assert result[1]["optionsJson"] == [
        {"key": "C", "text": "charlie"},
        {"key": "A", "text": "alpha"},
        {"key": "B", "text": "bravo"},
    ]


def test_apply_presentation_shuffle_rejects_mismatched_question_order() -> None:
    with pytest.raises(ValueError, match="permutation"):
        apply_presentation_shuffle(
            [_Q1, _Q2],
            question_order=["q1"],
            choice_orders={"q1": ["A", "B", "C"], "q2": ["X", "Y"]},
        )
