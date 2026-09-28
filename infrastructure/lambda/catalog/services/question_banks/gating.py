"""Pure module unlock rules from prior module quiz passes (RS-8)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from typing import Union

from services.question_banks.visibility import module_quiz_score_percent

DEFAULT_MODULE_QUIZ_PASS_PERCENT = 70

# Raw attempt: whole percent, or (correct_count, total_count).
AttemptScore = Union[int, tuple[int, int]]


def _attempt_score_percent(attempt: AttemptScore) -> int:
    if isinstance(attempt, int):
        return attempt
    correct_count, total_count = attempt
    return module_quiz_score_percent(
        correct_count=correct_count, total_count=total_count
    )


def _pass_threshold_for_module(
    module_id: str, pass_percent_by_module_id: Mapping[str, int]
) -> int:
    return pass_percent_by_module_id.get(
        module_id, DEFAULT_MODULE_QUIZ_PASS_PERCENT
    )


def module_is_passed(
    *,
    module_id: str,
    visible_quiz_module_ids: Set[str],
    pass_percent_by_module_id: Mapping[str, int],
    submitted_scores_by_module_id: Mapping[str, Sequence[AttemptScore]],
) -> bool:
    """True when the module does not gate (no visible quiz) or any attempt meets pass mark."""
    if module_id not in visible_quiz_module_ids:
        return True
    attempts = submitted_scores_by_module_id.get(module_id, ())
    if not attempts:
        return False
    threshold = _pass_threshold_for_module(module_id, pass_percent_by_module_id)
    return any(
        _attempt_score_percent(attempt) >= threshold for attempt in attempts
    )


def module_is_locked_for_student(
    ordered_module_ids: Sequence[str],
    target_module_id: str,
    visible_quiz_module_ids: Set[str],
    pass_percent_by_module_id: Mapping[str, int],
    submitted_scores_by_module_id: Mapping[str, Sequence[AttemptScore]],
) -> bool:
    """True when any earlier module with a visible quiz is not passed."""
    if target_module_id not in ordered_module_ids:
        raise ValueError("target_module_id is not in ordered_module_ids")
    target_index = ordered_module_ids.index(target_module_id)
    if target_index == 0:
        return False
    for earlier_id in ordered_module_ids[:target_index]:
        if earlier_id not in visible_quiz_module_ids:
            continue
        if not module_is_passed(
            module_id=earlier_id,
            visible_quiz_module_ids=visible_quiz_module_ids,
            pass_percent_by_module_id=pass_percent_by_module_id,
            submitted_scores_by_module_id=submitted_scores_by_module_id,
        ):
            return True
    return False


def compute_module_lock_states(
    ordered_module_ids: Sequence[str],
    visible_quiz_module_ids: Set[str],
    pass_percent_by_module_id: Mapping[str, int],
    submitted_scores_by_module_id: Mapping[str, Sequence[AttemptScore]],
) -> dict[str, bool]:
    """Map each module id to locked (True) or unlocked (False) for this student."""
    return {
        module_id: module_is_locked_for_student(
            ordered_module_ids,
            target_module_id=module_id,
            visible_quiz_module_ids=visible_quiz_module_ids,
            pass_percent_by_module_id=pass_percent_by_module_id,
            submitted_scores_by_module_id=submitted_scores_by_module_id,
        )
        for module_id in ordered_module_ids
    }
