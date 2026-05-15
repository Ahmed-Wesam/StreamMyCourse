"""Equal-weight MCQ grading for bound module-quiz submissions (§11.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from services.question_banks.presentation_shuffle import _option_keys_in_order


@dataclass(frozen=True)
class GradingRow:
    """One question's correct key and optional published options for validation."""

    question_id: str
    correct_option_key: str
    options_json: Any | None = None


@dataclass(frozen=True)
class GradedAnswer:
    question_id: str
    selected_option_key: str
    correct_option_key: str
    is_correct: bool


@dataclass(frozen=True)
class QuizGradeResult:
    correct_count: int
    total_count: int
    questions: tuple[GradedAnswer, ...]


def grade_bound_answers(
    *,
    question_ids: Sequence[str],
    answers: Mapping[str, str],
    grading_by_question_id: Mapping[str, GradingRow],
) -> QuizGradeResult:
    """Validate answers against bound ids, then score with equal weight per question.

    ``question_ids`` order is preserved in ``QuizGradeResult.questions``. Answer keys
    must match the bound id set exactly. When ``GradingRow.options_json`` is set,
    each selected key must appear in that question's published option keys.
    """

    ordered_ids = list(question_ids)
    if not ordered_ids:
        raise ValueError("at least one bound question is required")
    if len(set(ordered_ids)) != len(ordered_ids):
        raise ValueError("bound question ids must be unique")

    _validate_answer_key_set(expected=set(ordered_ids), answers=answers)
    _validate_grading_coverage(
        expected=set(ordered_ids), grading_by_question_id=grading_by_question_id
    )

    graded: list[GradedAnswer] = []
    correct = 0
    for question_id in ordered_ids:
        row = grading_by_question_id[question_id]
        selected_raw = answers[question_id]
        if not isinstance(selected_raw, str):
            raise ValueError("each answer must be a string option key")
        selected = selected_raw.strip()
        if not selected:
            raise ValueError("selected option key must be non-empty")

        correct_key_raw = row.correct_option_key
        if not isinstance(correct_key_raw, str):
            raise ValueError("correct option key must be a non-empty string")
        correct_key = correct_key_raw.strip()
        if not correct_key:
            raise ValueError("correct option key must be a non-empty string")

        if row.options_json is not None:
            allowed = _option_keys_in_order(row.options_json)
            if not allowed:
                raise ValueError(
                    "optionsJson must include at least one choice with a non-empty key"
                )
            allowed_set = set(allowed)
            if selected not in allowed_set:
                raise ValueError(
                    f"answers contain unknown option key(s) for question {question_id}: "
                    f"{selected}"
                )
            if correct_key not in allowed_set:
                raise ValueError(
                    f"grading row has unknown correct option key for question "
                    f"{question_id}: {correct_key}"
                )

        is_ok = selected == correct_key
        if is_ok:
            correct += 1
        graded.append(
            GradedAnswer(
                question_id=question_id,
                selected_option_key=selected,
                correct_option_key=correct_key,
                is_correct=is_ok,
            )
        )

    total = len(ordered_ids)
    return QuizGradeResult(
        correct_count=correct,
        total_count=total,
        questions=tuple(graded),
    )


def _validate_answer_key_set(
    *, expected: set[str], answers: Mapping[str, str]
) -> None:
    actual = set(answers.keys())
    if actual == expected:
        return
    unknown = sorted(actual - expected)
    if unknown:
        raise ValueError(
            "answers contain unknown question id(s): " + ", ".join(unknown)
        )
    raise ValueError(
        "answers missing question id(s): " + ", ".join(sorted(expected - actual))
    )


def _validate_grading_coverage(
    *,
    expected: set[str],
    grading_by_question_id: Mapping[str, GradingRow],
) -> None:
    actual = set(grading_by_question_id.keys())
    if actual == expected:
        return
    unknown = sorted(actual - expected)
    if unknown:
        raise ValueError(
            "grading rows include unknown question id(s): " + ", ".join(unknown)
        )
    raise ValueError(
        "grading rows missing question id(s): "
        + ", ".join(sorted(expected - actual))
    )
