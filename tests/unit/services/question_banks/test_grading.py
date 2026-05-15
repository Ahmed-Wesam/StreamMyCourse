"""Unit tests for module-quiz grading (QB-H slice 2)."""

from __future__ import annotations

import json

import pytest

from services.question_banks.grading import (
    GradingRow,
    grade_bound_answers,
)


def _opts() -> str:
    return json.dumps(
        [
            {"key": "A", "text": "a"},
            {"key": "B", "text": "b"},
        ]
    )


def test_equal_weight_all_correct() -> None:
    qids = ["q1", "q2"]
    grading = {
        "q1": GradingRow("q1", "A", _opts()),
        "q2": GradingRow("q2", "B", _opts()),
    }
    result = grade_bound_answers(
        question_ids=qids,
        answers={"q1": "A", "q2": "B"},
        grading_by_question_id=grading,
    )
    assert result.correct_count == 2
    assert result.total_count == 2
    assert [g.is_correct for g in result.questions] == [True, True]


def test_equal_weight_one_wrong() -> None:
    qids = ["q1", "q2"]
    grading = {
        "q1": GradingRow("q1", "A", _opts()),
        "q2": GradingRow("q2", "B", _opts()),
    }
    result = grade_bound_answers(
        question_ids=qids,
        answers={"q1": "A", "q2": "A"},
        grading_by_question_id=grading,
    )
    assert result.correct_count == 1
    assert result.total_count == 2
    assert [g.is_correct for g in result.questions] == [True, False]
    assert result.questions[1].correct_option_key == "B"
    assert result.questions[1].selected_option_key == "A"


def test_extra_answer_key_errors() -> None:
    with pytest.raises(ValueError, match="unknown question id"):
        grade_bound_answers(
            question_ids=["q1"],
            answers={"q1": "A", "q2": "B"},
            grading_by_question_id={"q1": GradingRow("q1", "A", _opts())},
        )


def test_missing_answer_key_errors() -> None:
    with pytest.raises(ValueError, match="missing question id"):
        grade_bound_answers(
            question_ids=["q1", "q2"],
            answers={"q1": "A"},
            grading_by_question_id={
                "q1": GradingRow("q1", "A", _opts()),
                "q2": GradingRow("q2", "B", _opts()),
            },
        )


def test_duplicate_bound_question_ids_rejected() -> None:
    with pytest.raises(ValueError, match="unique"):
        grade_bound_answers(
            question_ids=["q1", "q1"],
            answers={"q1": "A"},
            grading_by_question_id={"q1": GradingRow("q1", "A", _opts())},
        )


def test_empty_question_list_rejected() -> None:
    with pytest.raises(ValueError, match="at least one bound"):
        grade_bound_answers(
            question_ids=[],
            answers={},
            grading_by_question_id={},
        )


def test_selected_option_unknown_when_options_provided() -> None:
    with pytest.raises(ValueError, match="unknown option key"):
        grade_bound_answers(
            question_ids=["q1"],
            answers={"q1": "Z"},
            grading_by_question_id={"q1": GradingRow("q1", "A", _opts())},
        )


def test_empty_selected_option_key_rejected() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        grade_bound_answers(
            question_ids=["q1"],
            answers={"q1": "  "},
            grading_by_question_id={"q1": GradingRow("q1", "A", None)},
        )


def test_grading_without_options_validates_sets_and_non_empty_keys_only() -> None:
    qids = ["q1", "q2"]
    grading = {
        "q1": GradingRow("q1", "X", None),
        "q2": GradingRow("q2", "Y", None),
    }
    result = grade_bound_answers(
        question_ids=qids,
        answers={"q1": "X", "q2": "Z"},
        grading_by_question_id=grading,
    )
    assert result.correct_count == 1
    assert result.total_count == 2


def test_extra_grading_row_errors() -> None:
    with pytest.raises(ValueError, match="grading rows include unknown"):
        grade_bound_answers(
            question_ids=["q1"],
            answers={"q1": "A"},
            grading_by_question_id={
                "q1": GradingRow("q1", "A", _opts()),
                "q2": GradingRow("q2", "B", _opts()),
            },
        )


def test_missing_grading_row_errors() -> None:
    with pytest.raises(ValueError, match="grading rows missing"):
        grade_bound_answers(
            question_ids=["q1", "q2"],
            answers={"q1": "A", "q2": "B"},
            grading_by_question_id={"q1": GradingRow("q1", "A", _opts())},
        )


def test_question_order_preserved_in_breakdown() -> None:
    grading = {
        "a": GradingRow("a", "A", _opts()),
        "b": GradingRow("b", "B", _opts()),
    }
    result = grade_bound_answers(
        question_ids=["b", "a"],
        answers={"a": "A", "b": "B"},
        grading_by_question_id=grading,
    )
    assert [g.question_id for g in result.questions] == ["b", "a"]
