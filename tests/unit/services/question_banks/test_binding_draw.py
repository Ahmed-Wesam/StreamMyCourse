"""Unit tests for uniform question-id draw (QB-F slice 2)."""

from __future__ import annotations

import random

import pytest

from services.question_banks.binding_draw import draw_question_ids


_PUBLISHED = ["q1", "q2", "q3", "q4", "q5", "q6"]


def test_draw_question_ids_fixed_rng_returns_n_distinct_from_published() -> None:
    rng = random.Random(0)
    drawn = draw_question_ids(_PUBLISHED, 3, rng)
    assert drawn == ["q4", "q6", "q1"]
    assert len(drawn) == 3
    assert len(set(drawn)) == 3
    assert set(drawn).issubset(set(_PUBLISHED))


def test_draw_question_ids_raises_when_published_smaller_than_n() -> None:
    rng = random.Random(0)
    with pytest.raises(ValueError):
        draw_question_ids(["q1", "q2"], 3, rng)


def test_draw_question_ids_empty_published_with_n_at_least_one_raises() -> None:
    rng = random.Random(0)
    with pytest.raises(ValueError):
        draw_question_ids([], 1, rng)
