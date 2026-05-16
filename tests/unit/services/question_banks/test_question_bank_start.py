"""Unit tests for ``QuestionBankService.start_module_quiz`` (QB-F slice 3)."""

from __future__ import annotations

import json
import random
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

from services.common.errors import Conflict, NotFound
from services.question_banks.models import (
    BoundQuestion,
    ModuleQuiz,
    ModuleQuizAttempt,
    QuestionBank,
    StudentModuleQuizBinding,
)
from services.question_banks.service import QuestionBankService

_COURSE_ID = "course-11111111-1111-1111-1111-111111111111"
_OTHER_COURSE_ID = "course-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_MODULE_ID = "module-22222222-2222-2222-2222-222222222222"
_MQ_ID = "quiz-33333333-3333-3333-3333-333333333333"
_BANK_ID = "bank-44444444-4444-4444-4444-444444444444"
_STUDENT_A = "student-sub-a"
_STUDENT_B = "student-sub-b"
_ROLE = "student"

_MCQ_OPTIONS = [{"key": "A", "text": "choice A"}, {"key": "B", "text": "choice B"}]


def _published_module_quiz(*, course_id: str = _COURSE_ID) -> ModuleQuiz:
    return ModuleQuiz(
        id=_MQ_ID,
        courseId=course_id,
        moduleId=_MODULE_ID,
        questionBankId=_BANK_ID,
        servedCountN=2,
        createdAt="",
        updatedAt="",
    )


def _published_bank() -> QuestionBank:
    return QuestionBank(
        id=_BANK_ID,
        courseId=_COURSE_ID,
        name="Published bank",
        status="PUBLISHED",
        createdAt="",
        updatedAt="",
    )


def _binding(
    *,
    user_sub: str,
    question_ids: List[str],
) -> StudentModuleQuizBinding:
    return StudentModuleQuizBinding(
        id="binding-1",
        moduleQuizId=_MQ_ID,
        courseId=_COURSE_ID,
        userSub=user_sub,
        questionIds=question_ids,
    )


def _bound_questions(question_ids: List[str]) -> List[BoundQuestion]:
    options = json.dumps(_MCQ_OPTIONS)
    return [
        BoundQuestion(
            id=qid,
            promptText=f"prompt-{qid}",
            optionsJson=options,
        )
        for qid in question_ids
    ]


def _make_start_service(
    repo: MagicMock,
    *,
    course_status: str = "PUBLISHED",
    has_lesson_access: bool = True,
) -> QuestionBankService:
    authorizer = MagicMock()
    lesson_access = MagicMock()
    lesson_access.viewer_has_lesson_access.return_value = has_lesson_access
    course_read = MagicMock()
    course_read.get_course_status.return_value = course_status
    return QuestionBankService(
        course_mutate_authorizer=authorizer,
        question_bank_repo=repo,
        student_lesson_access=lesson_access,
        course_read=course_read,
    )


def _wire_start_gate(repo: MagicMock, *, module_quiz: ModuleQuiz | None = None) -> None:
    mq = module_quiz if module_quiz is not None else _published_module_quiz()
    repo.get_module_quiz_by_module_id.return_value = mq
    repo.get_question_bank_by_id.return_value = _published_bank()


def _wire_attempt_create(
    repo: MagicMock,
    *,
    binding: StudentModuleQuizBinding,
    question_order: List[str] | None = None,
    attempt_id: str = "attempt-11111111-1111-1111-1111-111111111111",
) -> None:
    """Default attempt layer: no open row; insert attempt 1 with identity shuffle."""
    order = question_order if question_order is not None else list(binding.questionIds)
    choice_orders = {qid: ["A", "B"] for qid in binding.questionIds}
    repo.get_open_attempt.return_value = None
    repo.get_latest_attempt.return_value = None
    repo.insert_attempt_with_shuffle.return_value = ModuleQuizAttempt(
        id=attempt_id,
        bindingId=binding.id,
        attemptNumber=1,
        status="in_progress",
        shuffledQuestionOrder=order,
        shuffledChoiceOrders=choice_orders,
        startedAt="2026-05-15T12:00:00Z",
    )

    def _rows_for_call(*, course_id: str, question_ids: List[str]) -> List[BoundQuestion]:
        return _bound_questions(question_ids)

    repo.list_student_bound_questions.side_effect = _rows_for_call

    def _shuffle_q(ids: List[str], _rng: random.Random) -> List[str]:
        return order

    def _shuffle_c(
        _rows: List[BoundQuestion], _rng: random.Random
    ) -> dict[str, list[str]]:
        return choice_orders

    repo._attempt_shuffle_patches = (_shuffle_q, _shuffle_c)


def _start_with_attempt_patches(
    svc: QuestionBankService,
    repo: MagicMock,
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    patches = getattr(repo, "_attempt_shuffle_patches", None)
    if patches is None:
        return svc.start_module_quiz(*args, **kwargs)
    shuffle_q, shuffle_c = patches
    with patch(
        "services.question_banks.service.shuffle_question_order",
        side_effect=shuffle_q,
    ):
        with patch(
            "services.question_banks.service.shuffle_choice_orders_for_questions",
            side_effect=shuffle_c,
        ):
            return svc.start_module_quiz(*args, **kwargs)


def test_start_not_found_when_course_not_published() -> None:
    repo = MagicMock()
    svc = _make_start_service(repo, course_status="DRAFT")

    with pytest.raises(NotFound, match="not available"):
        svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )

    repo.get_module_quiz_by_module_id.assert_not_called()


def test_start_not_found_when_no_lesson_access() -> None:
    repo = MagicMock()
    svc = _make_start_service(repo, has_lesson_access=False)

    with pytest.raises(NotFound, match="not available"):
        svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )

    repo.get_module_quiz_by_module_id.assert_not_called()


def test_start_not_found_when_module_quiz_belongs_to_other_course() -> None:
    repo = MagicMock()
    _wire_start_gate(
        repo,
        module_quiz=_published_module_quiz(course_id=_OTHER_COURSE_ID),
    )
    svc = _make_start_service(repo)

    with pytest.raises(NotFound, match="not available"):
        svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )

    repo.get_binding_for_student.assert_not_called()


def test_first_start_draws_inserts_and_returns_n_questions() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding(user_sub=_STUDENT_A, question_ids=ids)
    open_attempt = ModuleQuizAttempt(
        id="attempt-11111111-1111-1111-1111-111111111111",
        bindingId=binding.id,
        attemptNumber=1,
        status="in_progress",
        shuffledQuestionOrder=ids,
        shuffledChoiceOrders={"q1": ["A", "B"], "q2": ["A", "B"]},
        startedAt="2026-05-15T12:00:00Z",
    )
    repo.get_binding_for_student.side_effect = [None, binding]
    repo.list_published_question_ids.return_value = ["q1", "q2", "q3"]
    repo.list_student_bound_questions.return_value = _bound_questions(ids)
    repo.get_open_attempt.return_value = open_attempt
    svc = _make_start_service(repo)
    rng = random.Random(0)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=ids,
    ) as draw_mock:
        with patch(
            "services.question_banks.service.shuffle_question_order",
            return_value=ids,
        ):
            with patch(
                "services.question_banks.service.shuffle_choice_orders_for_questions",
                return_value={"q1": ["A", "B"], "q2": ["A", "B"]},
            ):
                out = svc.start_module_quiz(
                    _COURSE_ID,
                    _MODULE_ID,
                    cognito_sub=_STUDENT_A,
                    role=_ROLE,
                    rng=rng,
                )

    draw_mock.assert_called_once_with(["q1", "q2", "q3"], 2, rng)
    repo.insert_binding_with_questions_and_initial_attempt.assert_called_once()
    repo.insert_binding_with_questions.assert_not_called()
    repo.insert_attempt_with_shuffle.assert_not_called()
    assert out["servedCountN"] == 2
    assert out["phase"] == "in_progress"
    assert len(out["questions"]) == 2
    assert out["questionIds"] == ids
    assert [q["id"] for q in out["questions"]] == ids


def test_start_conflict_when_published_corpus_smaller_than_served_n() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    repo.get_binding_for_student.return_value = None
    repo.list_published_question_ids.return_value = ["q1"]
    svc = _make_start_service(repo)

    with pytest.raises(Conflict, match="cannot draw"):
        svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )

    repo.insert_binding_with_questions.assert_not_called()


def test_start_conflict_when_binding_question_id_count_mismatch() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    repo.get_binding_for_student.return_value = _binding(
        user_sub=_STUDENT_A, question_ids=["q1"]
    )
    svc = _make_start_service(repo)

    with pytest.raises(Conflict, match="binding is incomplete"):
        svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )

    repo.list_student_bound_questions.assert_not_called()


def test_start_conflict_when_bound_question_rows_missing() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    binding = _binding(user_sub=_STUDENT_A, question_ids=["q1", "q2"])
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = None
    repo.get_latest_attempt.return_value = None
    repo.list_student_bound_questions.return_value = _bound_questions(["q1"])
    svc = _make_start_service(repo)

    with pytest.raises(Conflict, match="could not be loaded"):
        svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )


def test_start_conflict_when_binding_missing_after_insert() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    repo.get_binding_for_student.side_effect = [None, None]
    repo.list_published_question_ids.return_value = ["q1", "q2"]
    repo.list_student_bound_questions.return_value = _bound_questions(["q1", "q2"])
    svc = _make_start_service(repo)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=["q1", "q2"],
    ):
        with patch(
            "services.question_banks.service.shuffle_question_order",
            return_value=["q1", "q2"],
        ):
            with patch(
                "services.question_banks.service.shuffle_choice_orders_for_questions",
                return_value={"q1": ["A", "B"], "q2": ["A", "B"]},
            ):
                with pytest.raises(
                    Conflict, match="could not be loaded after create"
                ):
                    svc.start_module_quiz(
                        _COURSE_ID,
                        _MODULE_ID,
                        cognito_sub=_STUDENT_A,
                        role=_ROLE,
                    )


def test_second_start_returns_same_ids_and_draw_called_once() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding(user_sub=_STUDENT_A, question_ids=ids)
    attempt = ModuleQuizAttempt(
        id="attempt-11111111-1111-1111-1111-111111111111",
        bindingId=binding.id,
        attemptNumber=1,
        status="in_progress",
        shuffledQuestionOrder=ids,
        shuffledChoiceOrders={"q1": ["A", "B"], "q2": ["A", "B"]},
        startedAt="",
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = attempt

    def _rows_for_call(*, course_id: str, question_ids: List[str]) -> List[BoundQuestion]:
        by_id = {row.id: row for row in _bound_questions(ids)}
        return [by_id[qid] for qid in question_ids]

    repo.list_student_bound_questions.side_effect = _rows_for_call
    svc = _make_start_service(repo)
    rng = random.Random(0)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=["should-not-be-used"],
    ) as draw_mock:
        first = svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            rng=rng,
        )
        second = svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            rng=rng,
        )

    draw_mock.assert_not_called()
    assert first["phase"] == second["phase"] == "in_progress"
    assert first["questionIds"] == second["questionIds"] == ids
    assert [q["id"] for q in first["questions"]] == ids
    assert [q["id"] for q in second["questions"]] == ids
    repo.insert_binding_with_questions.assert_not_called()
    repo.insert_attempt_with_shuffle.assert_not_called()
    assert repo.get_binding_for_student.call_count == 2


def test_section_9_5_existing_binding_unchanged_new_student_may_differ() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    repo.list_published_question_ids.return_value = [
        "q-old-1",
        "q-old-2",
        "q-new-3",
        "q-new-4",
    ]
    binding_a = _binding(user_sub=_STUDENT_A, question_ids=["q-old-1", "q-old-2"])
    binding_b = _binding(user_sub=_STUDENT_B, question_ids=["q-new-3", "q-new-4"])
    attempt_a = ModuleQuizAttempt(
        id="attempt-a",
        bindingId=binding_a.id,
        attemptNumber=1,
        status="in_progress",
        shuffledQuestionOrder=["q-old-1", "q-old-2"],
        shuffledChoiceOrders={
            "q-old-1": ["A", "B"],
            "q-old-2": ["A", "B"],
        },
        startedAt="",
    )
    repo.get_binding_for_student.side_effect = [
        binding_a,
        None,
        binding_b,
    ]
    attempt_b = ModuleQuizAttempt(
        id="attempt-b",
        bindingId=binding_b.id,
        attemptNumber=1,
        status="in_progress",
        shuffledQuestionOrder=["q-new-3", "q-new-4"],
        shuffledChoiceOrders={
            "q-new-3": ["A", "B"],
            "q-new-4": ["A", "B"],
        },
        startedAt="2026-05-15T12:00:00Z",
    )
    repo.get_open_attempt.side_effect = [attempt_a, attempt_b]

    def _rows_for_call(*, course_id: str, question_ids: List[str]) -> List[BoundQuestion]:
        return _bound_questions(question_ids)

    repo.list_student_bound_questions.side_effect = _rows_for_call
    svc = _make_start_service(repo)
    rng_a = random.Random(1)
    rng_b = random.Random(2)

    with patch(
        "services.question_banks.service.draw_question_ids",
        side_effect=[["q-should-not-redraw"], ["q-new-3", "q-new-4"]],
    ) as draw_mock:
        with patch(
            "services.question_banks.service.shuffle_question_order",
            return_value=["q-new-3", "q-new-4"],
        ):
            with patch(
                "services.question_banks.service.shuffle_choice_orders_for_questions",
                return_value={
                    "q-new-3": ["A", "B"],
                    "q-new-4": ["A", "B"],
                },
            ):
                out_a = svc.start_module_quiz(
                    _COURSE_ID,
                    _MODULE_ID,
                    cognito_sub=_STUDENT_A,
                    role=_ROLE,
                    rng=rng_a,
                )
                out_b = svc.start_module_quiz(
                    _COURSE_ID,
                    _MODULE_ID,
                    cognito_sub=_STUDENT_B,
                    role=_ROLE,
                    rng=rng_b,
                )

    assert draw_mock.call_count == 1
    assert out_a["phase"] == out_b["phase"] == "in_progress"
    assert out_a["questionIds"] == ["q-old-1", "q-old-2"]
    assert out_b["questionIds"] == ["q-new-3", "q-new-4"]
    repo.insert_binding_with_questions_and_initial_attempt.assert_called_once()
    repo.insert_binding_with_questions.assert_not_called()


def test_start_response_omits_correct_option_key() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding(user_sub=_STUDENT_A, question_ids=ids)
    attempt = ModuleQuizAttempt(
        id="attempt-11111111-1111-1111-1111-111111111111",
        bindingId=binding.id,
        attemptNumber=1,
        status="in_progress",
        shuffledQuestionOrder=ids,
        shuffledChoiceOrders={"q1": ["A", "B"], "q2": ["A"]},
        startedAt="",
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = attempt
    repo.list_student_bound_questions.return_value = [
        BoundQuestion(
            id="q1",
            promptText="What is 2+2?",
            optionsJson='[{"key":"A","text":"4"},{"key":"B","text":"5"}]',
        ),
        BoundQuestion(
            id="q2",
            promptText="Next?",
            optionsJson='[{"key":"A","text":"yes"}]',
        ),
    ]
    svc = _make_start_service(repo)

    out = svc.start_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
    )

    assert out["moduleQuizId"] == _MQ_ID
    assert out["phase"] == "in_progress"
    assert out["moduleId"] == _MODULE_ID
    assert out["servedCountN"] == 2
    assert len(out["questions"]) == 2
    question = out["questions"][0]
    assert question["id"] == "q1"
    assert question["promptText"] == "What is 2+2?"
    assert question["optionsJson"] == [
        {"key": "A", "text": "4"},
        {"key": "B", "text": "5"},
    ]
    assert "correctOptionKey" not in question
    dumped = str(out)
    assert "correctOptionKey" not in dumped


def test_start_on_conflict_reloads_binding_without_second_draw() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    binding = _binding(user_sub=_STUDENT_A, question_ids=["q1", "q2"])
    repo.get_binding_for_student.side_effect = [None, binding]
    repo.list_published_question_ids.return_value = ["q1", "q2", "q3"]
    repo.insert_binding_with_questions_and_initial_attempt.side_effect = Conflict(
        "binding exists"
    )
    repo.list_student_bound_questions.return_value = _bound_questions(["q9", "q8"])
    _wire_attempt_create(repo, binding=binding, question_order=["q1", "q2"])
    svc = _make_start_service(repo)
    rng = random.Random(0)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=["q9", "q8"],
    ) as draw_mock:
        out = _start_with_attempt_patches(
            svc,
            repo,
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            rng=rng,
        )

    draw_mock.assert_called_once()
    assert out["phase"] == "in_progress"
    assert out["questionIds"] == ["q1", "q2"]
    assert [q["id"] for q in out["questions"]] == ["q1", "q2"]
    assert repo.get_binding_for_student.call_count == 2
