"""Unit tests for ``QuestionBankService.submit_module_quiz`` (QB-H slice 3)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Conflict, NotFound
from services.question_banks.models import (
    ModuleQuiz,
    ModuleQuizAttempt,
    ModuleQuizAttemptBindingContext,
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
_STUDENT_B = "student-sub-b"
_ROLE = "student"
_ATTEMPT_ID = "attempt-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_BINDING_ID = "binding-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
_OPTS_JSON = '[{"key":"A","text":"choice A"},{"key":"B","text":"choice B"}]'


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


def _binding() -> StudentModuleQuizBinding:
    return StudentModuleQuizBinding(
        id=_BINDING_ID,
        moduleQuizId=_MQ_ID,
        courseId=_COURSE_ID,
        userSub=_STUDENT_A,
        questionIds=["q1", "q2"],
    )


def _attempt(*, status: str = "in_progress") -> ModuleQuizAttempt:
    return ModuleQuizAttempt(
        id=_ATTEMPT_ID,
        bindingId=_BINDING_ID,
        attemptNumber=1,
        status=status,
        shuffledQuestionOrder=["q2", "q1"],
        shuffledChoiceOrders={"q1": ["B", "A"], "q2": ["B", "A"]},
        startedAt="2026-05-15T12:00:00Z",
    )


def _ctx(*, status: str = "in_progress", user_sub: str = _STUDENT_A) -> ModuleQuizAttemptBindingContext:
    return ModuleQuizAttemptBindingContext(
        attempt=_attempt(status=status),
        moduleQuizId=_MQ_ID,
        courseId=_COURSE_ID,
        moduleId=_MODULE_ID,
        userSub=user_sub,
    )


def _grading_rows() -> list[PublishedQuestionGradingRow]:
    return [
        PublishedQuestionGradingRow(
            id="q1",
            promptText="prompt-q1",
            optionsJson=_OPTS_JSON,
            correctOptionKey="A",
        ),
        PublishedQuestionGradingRow(
            id="q2",
            promptText="prompt-q2",
            optionsJson=_OPTS_JSON,
            correctOptionKey="B",
        ),
    ]


def _make_service(repo: MagicMock) -> QuestionBankService:
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


def _wire_gate(repo: MagicMock) -> None:
    repo.get_module_quiz_by_module_id.return_value = _published_module_quiz()
    repo.get_question_bank_by_id.return_value = _published_bank()


def test_submit_happy_path_persists_and_returns_breakdown() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    repo.get_attempt_with_binding_rows.return_value = _ctx()
    repo.get_binding_for_student.return_value = _binding()
    repo.list_grading_rows_for_questions.return_value = _grading_rows()
    svc = _make_service(repo)

    out = svc.submit_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
        attempt_id=_ATTEMPT_ID,
        answers={"q1": "A", "q2": "B"},
    )

    repo.insert_submission_and_mark_submitted.assert_called_once_with(
        attempt_id=_ATTEMPT_ID,
        answers_json={"q1": "A", "q2": "B"},
        correct_count=2,
        total_count=2,
    )
    assert out["attemptId"] == _ATTEMPT_ID
    assert out["attemptNumber"] == 1
    assert out["correctCount"] == 2
    assert out["totalCount"] == 2
    assert len(out["questions"]) == 2
    assert out["questions"][0]["promptText"] == "prompt-q1"
    assert out["questions"][0]["selectedOptionKey"] == "A"
    assert out["questions"][0]["correctOptionKey"] == "A"
    assert out["questions"][0]["isCorrect"] is True


def test_submit_wrong_user_not_found() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    repo.get_attempt_with_binding_rows.return_value = _ctx(user_sub=_STUDENT_B)
    svc = _make_service(repo)

    with pytest.raises(NotFound, match="attempt"):
        svc.submit_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            attempt_id=_ATTEMPT_ID,
            answers={"q1": "A", "q2": "B"},
        )


def test_submit_already_submitted_conflict() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    repo.get_attempt_with_binding_rows.return_value = _ctx(status="submitted")
    svc = _make_service(repo)

    with pytest.raises(Conflict, match="already submitted"):
        svc.submit_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            attempt_id=_ATTEMPT_ID,
            answers={"q1": "A", "q2": "B"},
        )


def test_submit_bad_answers_bad_request() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    repo.get_attempt_with_binding_rows.return_value = _ctx()
    repo.get_binding_for_student.return_value = _binding()
    repo.list_grading_rows_for_questions.return_value = _grading_rows()
    svc = _make_service(repo)

    with pytest.raises(BadRequest, match="missing question id"):
        svc.submit_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            attempt_id=_ATTEMPT_ID,
            answers={"q1": "A"},
        )


def test_submit_duplicate_persist_conflict() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    repo.get_attempt_with_binding_rows.return_value = _ctx()
    repo.get_binding_for_student.return_value = _binding()
    repo.list_grading_rows_for_questions.return_value = _grading_rows()
    repo.insert_submission_and_mark_submitted.side_effect = Conflict(
        "Submission already recorded for this module quiz attempt"
    )
    svc = _make_service(repo)

    with pytest.raises(Conflict, match="Submission already recorded"):
        svc.submit_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            attempt_id=_ATTEMPT_ID,
            answers={"q1": "A", "q2": "B"},
        )


def test_submit_unknown_attempt_not_found() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    repo.get_attempt_with_binding_rows.return_value = None
    svc = _make_service(repo)

    with pytest.raises(NotFound, match="attempt"):
        svc.submit_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            attempt_id=_ATTEMPT_ID,
            answers={"q1": "A", "q2": "B"},
        )
