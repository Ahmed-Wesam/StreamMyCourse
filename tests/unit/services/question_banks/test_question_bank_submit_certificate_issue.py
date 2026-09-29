"""RS-12: quiz pass hooks CertificatesService.try_issue (fakes only)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

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
_ROLE = "student"
_ATTEMPT_ID = "attempt-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_BINDING_ID = "binding-bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
_OPTS_JSON = '[{"key":"A","text":"choice A"},{"key":"B","text":"choice B"}]'


class _FakeIssuer:
    def __init__(self, *, raise_on_issue: bool = False) -> None:
        self.calls: list[dict[str, str]] = []
        self.raise_on_issue = raise_on_issue

    def try_issue(self, *, user_sub: str, course_id: str, role: str) -> Any:
        self.calls.append(
            {"user_sub": user_sub, "course_id": course_id, "role": role}
        )
        if self.raise_on_issue:
            raise RuntimeError("issuer exploded")
        return None


def _published_module_quiz(*, pass_percent: int = 70) -> ModuleQuiz:
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


def _published_bank() -> QuestionBank:
    return QuestionBank(
        id=_BANK_ID,
        courseId=_COURSE_ID,
        name="Published bank",
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


def _make_service(
    repo: MagicMock, *, issuer: _FakeIssuer | None = None
) -> QuestionBankService:
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
        certificate_issuer=issuer,
    )


def _wire_gate(repo: MagicMock, *, pass_percent: int = 70) -> None:
    repo.get_module_quiz_by_module_id.return_value = _published_module_quiz(
        pass_percent=pass_percent
    )
    repo.get_question_bank_by_id.return_value = _published_bank()


def _wire_submit(repo: MagicMock) -> None:
    repo.get_attempt_with_binding_rows.return_value = _ctx()
    repo.get_binding_for_student.return_value = _binding()
    repo.list_grading_rows_for_questions.return_value = _grading_rows()


def test_passing_quiz_submit_calls_try_issue_once() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    _wire_submit(repo)
    issuer = _FakeIssuer()
    svc = _make_service(repo, issuer=issuer)

    out = svc.submit_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
        attempt_id=_ATTEMPT_ID,
        answers={"q1": "A", "q2": "B"},
    )

    assert out["passed"] is True
    assert issuer.calls == [
        {
            "user_sub": _STUDENT_A,
            "course_id": _COURSE_ID,
            "role": "student",
        }
    ]


def test_failing_quiz_submit_does_not_call_try_issue() -> None:
    repo = MagicMock()
    _wire_gate(repo, pass_percent=100)
    _wire_submit(repo)
    issuer = _FakeIssuer()
    svc = _make_service(repo, issuer=issuer)

    out = svc.submit_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
        attempt_id=_ATTEMPT_ID,
        # One wrong → 50% < 100%
        answers={"q1": "A", "q2": "A"},
    )

    assert out["passed"] is False
    assert issuer.calls == []


def test_raising_issuer_does_not_fail_passing_quiz_submit() -> None:
    repo = MagicMock()
    _wire_gate(repo)
    _wire_submit(repo)
    issuer = _FakeIssuer(raise_on_issue=True)
    svc = _make_service(repo, issuer=issuer)

    out = svc.submit_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT_A,
        role=_ROLE,
        attempt_id=_ATTEMPT_ID,
        answers={"q1": "A", "q2": "B"},
    )

    assert out["passed"] is True
    assert out["correctCount"] == 2
    assert len(issuer.calls) == 1
