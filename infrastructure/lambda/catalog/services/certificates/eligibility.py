"""Pure certificate eligibility rules for a single course (RS-12)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class QuizRequirement:
    """One visible module quiz (caller already filtered published bank + served)."""

    module_id: str
    passed: bool


@dataclass(frozen=True)
class AssignmentRequirement:
    """One assignment; only published + counts_toward_certificate items gate eligibility."""

    assignment_id: str
    status: str
    counts_toward_certificate: bool
    passed: bool


def is_course_eligible(
    *,
    quizzes: Sequence[QuizRequirement],
    assignments: Sequence[AssignmentRequirement],
) -> bool:
    """Return True when every quiz and every published flagged assignment is passed.

    Vacuous "nothing to pass" (zero quizzes and zero published flagged assignments)
    is ineligible. Draft and unflagged assignments never gate eligibility.
    """
    required_assignments = [
        a
        for a in assignments
        if a.status == "published" and a.counts_toward_certificate
    ]
    if not quizzes and not required_assignments:
        return False
    if any(not q.passed for q in quizzes):
        return False
    if any(not a.passed for a in required_assignments):
        return False
    return True
