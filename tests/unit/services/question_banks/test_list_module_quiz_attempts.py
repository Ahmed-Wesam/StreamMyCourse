"""RS-8 slice 4: GET .../modules/{moduleId}/quiz/attempts."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden, NotFound
from services.question_banks.models import ModuleQuiz, QuestionBank
from services.question_banks.service import QuestionBankService

_COURSE_ID = "11111111-1111-4111-8111-111111111111"
_MODULE_ID = "22222222-2222-4222-8222-222222222222"
_MQ_ID = "33333333-3333-4333-8333-333333333333"
_BANK_ID = "44444444-4444-4444-8444-444444444444"
_STUDENT = "student-sub-a"
_OTHER = "student-sub-b"
_ROLE = "student"


def _published_module_quiz() -> ModuleQuiz:
    return ModuleQuiz(
        id=_MQ_ID,
        courseId=_COURSE_ID,
        moduleId=_MODULE_ID,
        questionBankId=_BANK_ID,
        servedCountN=2,
        passPercent=70,
        createdAt="",
        updatedAt="",
    )


def _published_bank() -> QuestionBank:
    return QuestionBank(
        id=_BANK_ID,
        courseId=_COURSE_ID,
        name="Bank",
        status="PUBLISHED",
        createdAt="",
        updatedAt="",
    )


def _make_service(
    repo: MagicMock,
    *,
    has_lesson_access: bool = True,
    module_locked: bool = False,
) -> QuestionBankService:
    authorizer = MagicMock()
    course_read = MagicMock()
    course_read.get_course_status.return_value = "PUBLISHED"
    lesson_access = MagicMock()
    lesson_access.viewer_has_lesson_access.return_value = has_lesson_access
    module_lock = MagicMock()
    module_lock.is_module_locked_for_student.return_value = module_locked
    return QuestionBankService(
        course_mutate_authorizer=authorizer,
        question_bank_repo=repo,
        student_lesson_access=lesson_access,
        course_read=course_read,
        module_lock=module_lock,
    )


def _wire_visible_quiz(repo: MagicMock) -> None:
    repo.get_module_quiz_by_module_id.return_value = _published_module_quiz()
    repo.get_question_bank_by_id.return_value = _published_bank()


def test_list_attempts_returns_submitted_rows_oldest_first() -> None:
    repo = MagicMock()
    _wire_visible_quiz(repo)
    repo.list_submitted_module_quiz_attempts_for_student.return_value = [
        {
            "attemptId": "a1",
            "attemptNumber": 1,
            "correctCount": 1,
            "totalCount": 2,
            "scorePercent": 50,
            "passed": False,
            "submittedAt": "2026-01-01T00:00:00Z",
        },
        {
            "attemptId": "a2",
            "attemptNumber": 2,
            "correctCount": 2,
            "totalCount": 2,
            "scorePercent": 100,
            "passed": True,
            "submittedAt": "2026-01-02T00:00:00Z",
        },
    ]
    svc = _make_service(repo)

    out = svc.list_module_quiz_attempts(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT,
        role=_ROLE,
    )

    repo.list_submitted_module_quiz_attempts_for_student.assert_called_once_with(
        course_id=_COURSE_ID,
        module_id=_MODULE_ID,
        user_sub=_STUDENT,
        pass_percent=70,
    )
    assert [row["attemptId"] for row in out] == ["a1", "a2"]
    assert "answers" not in out[0]
    assert out[1]["passed"] is True


def test_list_attempts_empty_array_when_none_submitted() -> None:
    repo = MagicMock()
    _wire_visible_quiz(repo)
    repo.list_submitted_module_quiz_attempts_for_student.return_value = []
    svc = _make_service(repo)

    out = svc.list_module_quiz_attempts(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_STUDENT,
        role=_ROLE,
    )
    assert out == []


def test_list_attempts_404_without_lesson_access() -> None:
    repo = MagicMock()
    svc = _make_service(repo, has_lesson_access=False)

    with pytest.raises(NotFound):
        svc.list_module_quiz_attempts(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT,
            role=_ROLE,
        )


def test_list_attempts_403_when_module_locked() -> None:
    repo = MagicMock()
    _wire_visible_quiz(repo)
    svc = _make_service(repo, has_lesson_access=True, module_locked=True)

    with pytest.raises(Forbidden) as exc_info:
        svc.list_module_quiz_attempts(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT,
            role=_ROLE,
        )
    assert exc_info.value.code == "module_locked"
