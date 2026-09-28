"""Unit tests for module quiz gating (RS-8 slice 1)."""

from __future__ import annotations

from services.question_banks.gating import (
    DEFAULT_MODULE_QUIZ_PASS_PERCENT,
    compute_module_lock_states,
    module_is_locked_for_student,
    module_is_passed,
)

_M1, _M2, _M3, _M4 = "mod-1", "mod-2", "mod-3", "mod-4"
_ORDER = [_M1, _M2, _M3, _M4]


def test_first_module_always_unlocked() -> None:
    states = compute_module_lock_states(
        _ORDER,
        visible_quiz_module_ids={_M1},
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={},
    )
    assert states[_M1] is False
    assert module_is_locked_for_student(
        _ORDER,
        target_module_id=_M1,
        visible_quiz_module_ids={_M1},
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={},
    ) is False


def test_not_visible_quiz_module_does_not_gate() -> None:
    """Module 1 has attempts but quiz is not in the visible set — module 2 stays open."""
    scores = {_M1: [40]}
    visible: set[str] = set()
    assert module_is_locked_for_student(
        _ORDER,
        target_module_id=_M2,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id=scores,
    ) is False
    states = compute_module_lock_states(
        _ORDER[:2],
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id=scores,
    )
    assert states[_M2] is False


def test_gap_module_without_visible_quiz_does_not_gate() -> None:
    """Module 2 has no visible quiz; only module 1 gates module 3."""
    visible = {_M1, _M3}
    scores_pass_m1 = {_M1: [80]}
    assert module_is_locked_for_student(
        _ORDER,
        target_module_id=_M3,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id=scores_pass_m1,
    ) is False

    scores_fail_m1 = {_M1: [50]}
    assert module_is_locked_for_student(
        _ORDER,
        target_module_id=_M3,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id=scores_fail_m1,
    ) is True


def test_quiz_only_visible_module_gates_later_modules() -> None:
    """Module 1 is quiz-only (visible) with no pass — module 2 locked."""
    visible = {_M1}
    assert module_is_locked_for_student(
        [_M1, _M2],
        target_module_id=_M2,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={},
    ) is True
    assert module_is_locked_for_student(
        [_M1, _M2],
        target_module_id=_M2,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={_M1: [DEFAULT_MODULE_QUIZ_PASS_PERCENT]},
    ) is False


def test_one_earlier_miss_locks_all_later_modules() -> None:
    visible = {_M1, _M2}
    scores = {_M1: [90], _M2: [40]}
    states = compute_module_lock_states(
        _ORDER,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id=scores,
    )
    assert states[_M1] is False
    assert states[_M2] is False
    assert states[_M3] is True
    assert states[_M4] is True


def test_later_fail_after_earlier_pass_does_not_re_lock() -> None:
    """A failing retry on module 1 does not undo an earlier passing attempt."""
    visible = {_M1}
    scores = {_M1: [85, 30]}
    assert module_is_passed(
        module_id=_M1,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id=scores,
    )
    assert module_is_locked_for_student(
        [_M1, _M2],
        target_module_id=_M2,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id=scores,
    ) is False


def test_raising_pass_mark_re_locks() -> None:
    visible = {_M1}
    scores = {_M1: [75]}
    assert module_is_passed(
        module_id=_M1,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={_M1: 70},
        submitted_scores_by_module_id=scores,
    )
    assert module_is_passed(
        module_id=_M1,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={_M1: 80},
        submitted_scores_by_module_id=scores,
    ) is False
    assert module_is_locked_for_student(
        [_M1, _M2],
        target_module_id=_M2,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={_M1: 80},
        submitted_scores_by_module_id=scores,
    ) is True


def test_lowering_pass_mark_unlocks() -> None:
    visible = {_M1}
    scores = {_M1: [72]}
    assert module_is_locked_for_student(
        [_M1, _M2],
        target_module_id=_M2,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={_M1: 75},
        submitted_scores_by_module_id=scores,
    ) is True
    assert module_is_locked_for_student(
        [_M1, _M2],
        target_module_id=_M2,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={_M1: 70},
        submitted_scores_by_module_id=scores,
    ) is False


def test_module_is_passed_accepts_correct_total_pairs() -> None:
    """Uses module_quiz_score_percent: 2/3 rounds to 67%, below default 70."""
    visible = {_M1}
    assert module_is_passed(
        module_id=_M1,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={_M1: [(2, 3)]},
    ) is False
    assert module_is_passed(
        module_id=_M1,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={_M1: [(7, 10)]},
    ) is True


def test_visible_quiz_with_no_submissions_not_passed() -> None:
    visible = {_M1}
    assert module_is_passed(
        module_id=_M1,
        visible_quiz_module_ids=visible,
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={},
    ) is False


def test_module_without_visible_quiz_is_passed_for_gating() -> None:
    assert module_is_passed(
        module_id=_M2,
        visible_quiz_module_ids={_M1},
        pass_percent_by_module_id={},
        submitted_scores_by_module_id={},
    ) is True
