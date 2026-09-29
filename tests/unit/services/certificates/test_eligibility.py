"""Unit tests for course certificate eligibility (RS-12 eligibility slice)."""

from __future__ import annotations

from services.certificates.eligibility import (
    AssignmentRequirement,
    QuizRequirement,
    is_course_eligible,
)


def test_all_quizzes_passed_with_no_published_flagged_assignments_is_eligible() -> None:
    assert (
        is_course_eligible(
            quizzes=[
                QuizRequirement(module_id="m1", passed=True),
                QuizRequirement(module_id="m2", passed=True),
            ],
            assignments=[],
        )
        is True
    )


def test_all_published_flagged_assignments_passed_with_no_quizzes_is_eligible() -> None:
    assert (
        is_course_eligible(
            quizzes=[],
            assignments=[
                AssignmentRequirement(
                    assignment_id="a1",
                    status="published",
                    counts_toward_certificate=True,
                    passed=True,
                ),
                AssignmentRequirement(
                    assignment_id="a2",
                    status="published",
                    counts_toward_certificate=True,
                    passed=True,
                ),
            ],
        )
        is True
    )


def test_quizzes_and_published_flagged_assignments_all_passed_is_eligible() -> None:
    assert (
        is_course_eligible(
            quizzes=[QuizRequirement(module_id="m1", passed=True)],
            assignments=[
                AssignmentRequirement(
                    assignment_id="a1",
                    status="published",
                    counts_toward_certificate=True,
                    passed=True,
                ),
            ],
        )
        is True
    )


def test_no_quizzes_and_no_assignments_is_ineligible() -> None:
    assert is_course_eligible(quizzes=[], assignments=[]) is False


def test_failed_quiz_is_ineligible() -> None:
    assert (
        is_course_eligible(
            quizzes=[
                QuizRequirement(module_id="m1", passed=True),
                QuizRequirement(module_id="m2", passed=False),
            ],
            assignments=[],
        )
        is False
    )


def test_failed_published_flagged_assignment_is_ineligible() -> None:
    assert (
        is_course_eligible(
            quizzes=[],
            assignments=[
                AssignmentRequirement(
                    assignment_id="a1",
                    status="published",
                    counts_toward_certificate=True,
                    passed=False,
                ),
            ],
        )
        is False
    )


def test_failed_published_unflagged_assignment_is_ignored() -> None:
    assert (
        is_course_eligible(
            quizzes=[QuizRequirement(module_id="m1", passed=True)],
            assignments=[
                AssignmentRequirement(
                    assignment_id="a1",
                    status="published",
                    counts_toward_certificate=False,
                    passed=False,
                ),
            ],
        )
        is True
    )


def test_draft_flagged_assignment_does_not_block() -> None:
    assert (
        is_course_eligible(
            quizzes=[QuizRequirement(module_id="m1", passed=True)],
            assignments=[
                AssignmentRequirement(
                    assignment_id="a1",
                    status="draft",
                    counts_toward_certificate=True,
                    passed=False,
                ),
            ],
        )
        is True
    )


def test_draft_flagged_assignment_does_not_count_as_a_requirement() -> None:
    assert (
        is_course_eligible(
            quizzes=[],
            assignments=[
                AssignmentRequirement(
                    assignment_id="a1",
                    status="draft",
                    counts_toward_certificate=True,
                    passed=True,
                ),
            ],
        )
        is False
    )


def test_failed_quiz_stays_ineligible_lessons_are_not_an_input() -> None:
    """Eligibility has no lesson parameter; lessons cannot override a failed quiz."""
    assert (
        is_course_eligible(
            quizzes=[QuizRequirement(module_id="m1", passed=False)],
            assignments=[],
        )
        is False
    )
