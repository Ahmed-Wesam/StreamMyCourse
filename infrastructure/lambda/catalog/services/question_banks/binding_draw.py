"""Uniform random draw of published question ids for student quiz binding."""

from __future__ import annotations

import random


def draw_question_ids(
    published_ids: list[str], n: int, rng: random.Random
) -> list[str]:
    if n < 0:
        raise ValueError("n must be non-negative")
    if len(published_ids) < n:
        raise ValueError(
            f"cannot draw {n} questions from {len(published_ids)} published"
        )
    return rng.sample(published_ids, n)
