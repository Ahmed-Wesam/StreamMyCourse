"""RS-8 slice 4: scorePercent, passPercent, passed on submit and latest_results start."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.question_banks.models import (
    ModuleQuiz,
    ModuleQuizAttempt,
    ModuleQuizAttemptBindingContext,
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
_ATTEMPT_ID = "attempt-55555555-5555-5555-5555-555555555555"
_STUDENT = "student-sub-a"
_ROLE = "student"
_OPTS = '[{"key":"A","text":"a"},{"key":"B","text":"b"}]'


def _module_quiz(*, pass_percent: int = 70) -> ModuleQuiz:
    return ModuleQuiz(
        id=_MQ_ID,
        courseId=_COURSE_ID,
        moduleId=_MODULE_ID,
        questionBankId=_BANK_ID,
        servedCountN=2,
        passPercent=pass_percent,
        createdAt="",
        updatedAt="",
    )


def _bank() -> QuestionBank:
    return QuestionBank(
        id=_BANK_ID,
        courseId=_COURSE_ID,
        name="B",
        status="PUBLISHED",
        createdAt="",
        updatedAt="",
    )


def _grading_rows() -> list[PublishedQuestionGradingRow]:
    return [
        PublishedQuestionGradingRow(
            id="q1",
            promptText="p1",
            optionsJson=_OPTS,
            correctOptionKey="A",
        ),
        PublishedQuestionGradingRow(
            id="q2",
            promptText="p2",
            optionsJson=_OPTS,
            correctOptionKey="B",
        ),
    ]


def _service(repo: MagicMock) -> QuestionBankService:
    course_read = MagicMock()
    course_read.get_course_status.return_value = "PUBLISHED"
    lesson_access = MagicMock()
    lesson_access.viewer_has_lesson_access.return_value = True
    module_lock = MagicMock()
    module_lock.is_module_locked_for_student.return_value = False
    return QuestionBankService(
        course_mutate_authorizer=MagicMock(),
        question_bank_repo=repo,
        student_lesson_access=lesson_access,
        course_read=course_read,
        module_lock=module_lock,
    )


def _wire_gate(repo: MagicMock, *, pass_percent: int = 70) -> None:
    repo.get_module_quiz_by_module_id.return_value = _module_quiz(
        pass_percent=pass_percent
    )
    repo.get_question_bank_by_id.return_value = _bank()


def test_submit_includes_pass_outcome_fields() -> None:
    repo = MagicMock()
    _wire_gate(repo, pass_percent=70)
    ctx = ModuleQuizAttemptBindingContext(
        attempt=ModuleQuizAttempt(
            id=_ATTEMPT_ID,
            bindingId="bind-1",
            attemptNumber=1,
            status="in_progress",
            shuffledQuestionOrder=["q1", "q2"],
            shuffledChoiceOrders={"q1": ["A", "B"], "q2": ["A", "B"]},
            startedAt="",
        ),
        moduleQuizId=_MQ_ID,
        courseId=_COURSE_ID,
        moduleId=_MODULE_ID,
        userSub=_STUDENT,
    )
    repo.get_attempt_with_binding_rows.return_value = ctx
    repo.get_binding_for_student.return_value = StudentModuleQuizBinding(
        id="bind-1",
        moduleQuizId=_MQ_ID,
        courseId=_COURSE_ID,
        userSub=_STUDENT,
        questionIds=["q1", "q2"],
    )
    repo.list_grading_rows_for_questions.return_value = _grading_rows()
    svc = _service(repo)

    out = svc.submit_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT,
        role=_ROLE,
        attempt_id=_ATTEMPT_ID,
        answers={"q1": "A", "q2": "B"},
    )

    assert out["scorePercent"] == 100
    assert out["passPercent"] == 70
    assert out["passed"] is True


def test_latest_results_start_includes_pass_outcome_fields() -> None:
    repo = MagicMock()
    _wire_gate(repo, pass_percent=80)
    binding = StudentModuleQuizBinding(
        id="bind-1",
        moduleQuizId=_MQ_ID,
        courseId=_COURSE_ID,
        userSub=_STUDENT,
        questionIds=["q1", "q2"],
    )
    repo.get_binding_for_student.return_value = binding
    repo.get_open_attempt.return_value = None
    repo.get_latest_attempt.return_value = ModuleQuizAttempt(
        id=_ATTEMPT_ID,
        bindingId="bind-1",
        attemptNumber=1,
        status="submitted",
        shuffledQuestionOrder=["q1", "q2"],
        shuffledChoiceOrders={"q1": ["A", "B"], "q2": ["A", "B"]},
        startedAt="",
        submittedAt="2026-01-01T00:00:00Z",
    )
    repo.get_latest_submission_for_binding.return_value = ModuleQuizSubmissionSnapshot(
        attemptId=_ATTEMPT_ID,
        attemptNumber=1,
        questionOrder=["q1", "q2"],
        answersJson={"q1": "A", "q2": "A"},
        correctCount=1,
        totalCount=2,
        submittedAt="2026-01-01T00:00:00Z",
    )
    repo.list_grading_rows_for_questions.return_value = _grading_rows()
    svc = _service(repo)

    out = svc.start_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT,
        role=_ROLE,
        retake=False,
    )

    assert out["phase"] == "latest_results"
    assert out["scorePercent"] == 50
    assert out["passPercent"] == 80
    assert out["passed"] is False
