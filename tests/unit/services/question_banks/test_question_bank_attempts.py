"""Unit tests for module-quiz attempt layer in start_module_quiz (QB-G slice 3)."""

from __future__ import annotations

import json
import random
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from services.common.errors import Conflict
from services.question_banks.models import (
    BoundQuestion,
    ModuleQuiz,
    ModuleQuizAttempt,
    ModuleQuizSubmissionSnapshot,
    PublishedQuestionGradingRow,
    QuestionBank,
    StudentModuleQuizBinding,
)
from services.question_banks.service import QuestionBankService

_COURSE_ID = "course-11111111-1111-1111-1111-111111111111"
_MODULE_ID = "module-22222222-2222-2222-2222-222222222222"
_MQ_ID = "quiz-33333333-3333-3333-3333-333333333333"
_BANK_ID = "bank-44444444-4444-4444-4444-444444444444"
_STUDENT_A = "student-sub-a"
_ROLE = "student"


def _published_module_quiz() -> ModuleQuiz:
    return ModuleQuiz(
        id=_MQ_ID,
        courseId=_COURSE_ID,
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
        status="PUBLISHED",
        createdAt="",
        updatedAt="",
    )


def _bound_questions(question_ids: list[str]) -> list[BoundQuestion]:
    return [
        BoundQuestion(
            id=qid,
            promptText=f"prompt-{qid}",
            optionsJson='[{"key":"A","text":"choice A"},{"key":"B","text":"choice B"}]',
        )
        for qid in question_ids
    ]


def _make_start_service(repo: MagicMock) -> QuestionBankService:
    authorizer = MagicMock()
    lesson_access = MagicMock()
    lesson_access.viewer_has_lesson_access.return_value = True
    course_read = MagicMock()
    course_read.get_course_status.return_value = "PUBLISHED"
    return QuestionBankService(
        course_mutate_authorizer=authorizer,
        question_bank_repo=repo,
        student_lesson_access=lesson_access,
        course_read=course_read,
    )


def _wire_start_gate(repo: MagicMock) -> None:
    repo.get_module_quiz_by_module_id.return_value = _published_module_quiz()
    repo.get_question_bank_by_id.return_value = _published_bank()

_ATTEMPT_ID_1 = "attempt-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_ATTEMPT_ID_2 = "attempt-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
_BINDING_ID = "binding-cccccccc-cccc-cccc-cccc-cccccccccccc"


def _attempt(
    *,
    attempt_id: str = _ATTEMPT_ID_1,
    binding_id: str = _BINDING_ID,
    attempt_number: int = 1,
    status: str = "in_progress",
    question_order: List[str] | None = None,
    choice_orders: dict[str, list[str]] | None = None,
    submitted_at: str | None = None,
) -> ModuleQuizAttempt:
    return ModuleQuizAttempt(
        id=attempt_id,
        bindingId=binding_id,
        attemptNumber=attempt_number,
        status=status,
        shuffledQuestionOrder=question_order or ["q2", "q1"],
        shuffledChoiceOrders=choice_orders
        or {"q1": ["B", "A"], "q2": ["B", "A"]},
        startedAt="2026-05-15T12:00:00Z",
        submittedAt=submitted_at,
    )


def _binding_with_id(
    question_ids: List[str], *, user_sub: str = _STUDENT_A
) -> StudentModuleQuizBinding:
    return StudentModuleQuizBinding(
        id=_BINDING_ID,
        moduleQuizId=_MQ_ID,
        courseId=_COURSE_ID,
        userSub=user_sub,
        questionIds=question_ids,
    )


def test_first_start_creates_attempt_one_with_shuffle_fields() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    open_attempt = _attempt(
        attempt_id=_ATTEMPT_ID_1,
        question_order=["q2", "q1"],
    )
    repo.get_binding_for_student.side_effect = [None, binding]
    repo.list_published_question_ids.return_value = ["q1", "q2", "q3"]
    all_rows = {row.id: row for row in _bound_questions(ids)}

    def _rows_for_call(*, course_id: str, question_ids: list[str]) -> list[BoundQuestion]:
        return [all_rows[qid] for qid in question_ids]

    repo.list_student_bound_questions.side_effect = _rows_for_call
    repo.get_open_attempt.return_value = open_attempt
    svc = _make_start_service(repo)
    rng = random.Random(42)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=ids,
    ):
        with patch(
            "services.question_banks.service.shuffle_question_order",
            return_value=["q2", "q1"],
        ) as shuffle_q:
            with patch(
                "services.question_banks.service.shuffle_choice_orders_for_questions",
                return_value={"q1": ["B", "A"], "q2": ["B", "A"]},
            ) as shuffle_c:
                out = svc.start_module_quiz(
                    _COURSE_ID,
                    _MODULE_ID,
                    cognito_sub=_STUDENT_A,
                    role=_ROLE,
                    rng=rng,
                )

    shuffle_q.assert_called_once_with(ids, rng)
    shuffle_c.assert_called_once()
    repo.insert_binding_with_questions_and_initial_attempt.assert_called_once_with(
        module_quiz_id=_MQ_ID,
        course_id=_COURSE_ID,
        user_sub=_STUDENT_A,
        question_ids=ids,
        shuffled_question_order=["q2", "q1"],
        shuffled_choice_orders={"q1": ["B", "A"], "q2": ["B", "A"]},
    )
    repo.insert_attempt_with_shuffle.assert_not_called()
    repo.list_student_bound_questions.assert_called_with(
        course_id=_COURSE_ID,
        question_ids=["q2", "q1"],
    )
    assert out["attemptId"] == _ATTEMPT_ID_1
    assert out["attemptNumber"] == 1
    assert out["questionIds"] == ["q2", "q1"]
    assert [q["id"] for q in out["questions"]] == ["q2", "q1"]
    assert out["questions"][0]["id"] == "q2"
    assert out["phase"] == "in_progress"


def test_second_start_in_progress_returns_same_attempt_and_shuffle() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    attempt = _attempt(
        question_order=["q2", "q1"],
        choice_orders={"q1": ["B", "A"], "q2": ["B", "A"]},
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = attempt
    repo.list_student_bound_questions.return_value = _bound_questions(["q2", "q1"])
    svc = _make_start_service(repo)

    first = svc.start_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
    )
    second = svc.start_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
    )

    repo.insert_attempt_with_shuffle.assert_not_called()
    repo.get_latest_attempt.assert_not_called()
    assert first["phase"] == second["phase"] == "in_progress"
    assert first["questionIds"] == second["questionIds"] == ["q2", "q1"]
    assert first["questions"][0]["optionsJson"] == second["questions"][0]["optionsJson"]


def test_upgrade_path_binding_without_attempt_creates_attempt_one() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = None
    repo.get_latest_attempt.return_value = None
    repo.insert_attempt_with_shuffle.return_value = _attempt(
        attempt_id=_ATTEMPT_ID_1,
        question_order=["q2", "q1"],
    )
    repo.list_student_bound_questions.return_value = _bound_questions(ids)
    svc = _make_start_service(repo)

    with patch(
        "services.question_banks.service.shuffle_question_order",
        return_value=["q1", "q2"],
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
            )

    repo.insert_binding_with_questions.assert_not_called()
    assert out["phase"] == "in_progress"
    assert out["attemptNumber"] == 1
    assert out["attemptId"] == _ATTEMPT_ID_1


def test_after_submitted_start_without_retake_returns_latest_results() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    submitted = _attempt(
        attempt_id=_ATTEMPT_ID_1,
        attempt_number=1,
        status="submitted",
        question_order=["q2", "q1"],
        choice_orders={"q1": ["B", "A"], "q2": ["B", "A"]},
        submitted_at="2026-05-15T13:00:00Z",
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = None
    repo.get_latest_attempt.return_value = submitted
    repo.get_latest_submission_for_binding.return_value = ModuleQuizSubmissionSnapshot(
        attemptId=_ATTEMPT_ID_1,
        attemptNumber=1,
        answersJson={"q1": "A", "q2": "B"},
        correctCount=2,
        totalCount=2,
        submittedAt="2026-05-15T13:00:00Z",
    )
    opts = '[{"key":"A","text":"choice A"},{"key":"B","text":"choice B"}]'
    repo.list_grading_rows_for_questions.return_value = [
        PublishedQuestionGradingRow(
            id="q1",
            promptText="prompt-q1",
            optionsJson=opts,
            correctOptionKey="A",
        ),
        PublishedQuestionGradingRow(
            id="q2",
            promptText="prompt-q2",
            optionsJson=opts,
            correctOptionKey="B",
        ),
    ]
    svc = _make_start_service(repo)

    out = svc.start_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
        retake=False,
    )

    repo.insert_attempt_with_shuffle.assert_not_called()
    assert out["phase"] == "latest_results"
    assert out["latestSubmission"]["attemptNumber"] == 1
    assert out["latestSubmission"]["correctCount"] == 2
    assert out["latestSubmission"]["totalCount"] == 2
    assert len(out["latestSubmission"]["questions"]) == 2
    assert out["latestSubmission"]["questions"][0]["isCorrect"] is True


def test_after_submitted_retake_true_inserts_new_attempt_with_shuffle() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    submitted = _attempt(
        attempt_id=_ATTEMPT_ID_1,
        attempt_number=1,
        status="submitted",
        question_order=["q2", "q1"],
        choice_orders={"q1": ["B", "A"], "q2": ["B", "A"]},
        submitted_at="2026-05-15T13:00:00Z",
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = None
    repo.get_latest_attempt.return_value = submitted
    repo.insert_attempt_with_shuffle.return_value = _attempt(
        attempt_id=_ATTEMPT_ID_2,
        attempt_number=2,
        question_order=["q1", "q2"],
        choice_orders={"q1": ["A", "B"], "q2": ["A", "B"]},
    )
    repo.list_student_bound_questions.return_value = _bound_questions(ids)
    svc = _make_start_service(repo)

    with patch(
        "services.question_banks.service.shuffle_question_order",
        return_value=["q1", "q2"],
    ) as shuffle_q:
        with patch(
            "services.question_banks.service.shuffle_choice_orders_for_questions",
            return_value={"q1": ["A", "B"], "q2": ["A", "B"]},
        ):
            out = svc.start_module_quiz(
                _COURSE_ID,
                _MODULE_ID,
                cognito_sub=_STUDENT_A,
                role=_ROLE,
                rng=random.Random(1),
                retake=True,
            )

    shuffle_q.assert_called_once()
    repo.insert_attempt_with_shuffle.assert_called_once_with(
        binding_id=_BINDING_ID,
        attempt_number=2,
        shuffled_question_order=["q1", "q2"],
        shuffled_choice_orders={"q1": ["A", "B"], "q2": ["A", "B"]},
    )
    assert out["phase"] == "in_progress"
    assert out["attemptId"] == _ATTEMPT_ID_2
    assert out["attemptNumber"] == 2
    assert out["questionIds"] == ["q1", "q2"]
    assert set(out["questionIds"]) == set(ids)


def test_corrupt_persisted_shuffle_raises_conflict() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    corrupt = _attempt(
        question_order=["q1", "q-missing"],
        choice_orders={"q1": ["A", "B"], "q2": ["A", "B"]},
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = corrupt
    svc = _make_start_service(repo)

    with pytest.raises(Conflict, match="unknown question id"):
        svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )

    repo.insert_attempt_with_shuffle.assert_not_called()
    repo.list_student_bound_questions.assert_not_called()


def test_insert_attempt_conflict_rereads_open_attempt() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    winner = _attempt(
        question_order=["q2", "q1"],
        choice_orders={"q1": ["B", "A"], "q2": ["B", "A"]},
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.side_effect = [None, winner]
    repo.get_latest_attempt.return_value = None
    repo.insert_attempt_with_shuffle.side_effect = Conflict("in progress")
    repo.list_student_bound_questions.return_value = _bound_questions(["q2", "q1"])
    svc = _make_start_service(repo)

    with patch(
        "services.question_banks.service.shuffle_question_order",
        return_value=["q-should-not-win"],
    ):
        out = svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
        )

    assert out["phase"] == "in_progress"


def test_bound_question_id_set_unchanged_across_attempts() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = None
    repo.get_latest_attempt.return_value = None
    repo.insert_attempt_with_shuffle.return_value = _attempt(
        attempt_id=_ATTEMPT_ID_1,
        question_order=["q2", "q1"],
    )
    repo.list_student_bound_questions.return_value = _bound_questions(ids)
    svc = _make_start_service(repo)

    with patch(
        "services.question_banks.service.shuffle_question_order",
        return_value=["q2", "q1"],
    ):
        with patch(
            "services.question_banks.service.shuffle_choice_orders_for_questions",
            return_value={"q1": ["B", "A"], "q2": ["A", "B"]},
        ):
            out = svc.start_module_quiz(
                _COURSE_ID,
                _MODULE_ID,
                cognito_sub=_STUDENT_A,
                role=_ROLE,
            )

    assert out["phase"] == "in_progress"
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    binding = _binding_with_id(ids)
    attempt = _attempt(
        question_order=["q1", "q2"],
        choice_orders={"q1": ["A", "B"], "q2": ["A"]},
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = attempt
    repo.list_student_bound_questions.return_value = [
        BoundQuestion(
            id="q1",
            promptText="What?",
            optionsJson=json.dumps(
                [{"key": "A", "text": "4"}, {"key": "B", "text": "5"}]
            ),
        ),
        BoundQuestion(
            id="q2",
            promptText="Next?",
            optionsJson=json.dumps([{"key": "A", "text": "yes"}]),
        ),
    ]
    svc = _make_start_service(repo)

    out = svc.start_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
    )

    assert out["phase"] == "in_progress"
