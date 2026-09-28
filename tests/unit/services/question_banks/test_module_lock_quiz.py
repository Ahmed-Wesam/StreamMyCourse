"""RS-8 slice 3: module_locked on start/submit after access gates."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden, NotFound
from services.question_banks.models import ModuleQuiz, QuestionBank
from services.question_banks.service import QuestionBankService

_COURSE_ID = "course-11111111-1111-1111-1111-111111111111"
_MODULE_ID = "module-22222222-2222-2222-2222-222222222222"
_MQ_ID = "quiz-33333333-3333-3333-3333-333333333333"
_BANK_ID = "bank-44444444-4444-4444-4444-444444444444"
_STUDENT = "student-sub-a"
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
        name="Published bank",
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
    lesson_access = MagicMock()
    lesson_access.viewer_has_lesson_access.return_value = has_lesson_access
    course_read = MagicMock()
    course_read.get_course_status.return_value = "PUBLISHED"
    module_lock = MagicMock()
    module_lock.is_module_locked_for_student.return_value = module_locked
    return QuestionBankService(
        course_mutate_authorizer=authorizer,
        question_bank_repo=repo,
        student_lesson_access=lesson_access,
        course_read=course_read,
        module_lock=module_lock,
    )


def _wire_start_gate(repo: MagicMock) -> None:
    repo.get_module_quiz_by_module_id.return_value = _published_module_quiz()
    repo.get_question_bank_by_id.return_value = _published_bank()


def test_start_module_quiz_404_without_lesson_access() -> None:
    repo = MagicMock()
    svc = _make_service(repo, has_lesson_access=False, module_locked=True)
    with pytest.raises(NotFound):
        svc.start_module_quiz(
            _COURSE_ID, _MODULE_ID, cognito_sub=_STUDENT, role=_ROLE
        )
    repo.get_module_quiz_by_module_id.assert_not_called()


def test_start_module_quiz_403_module_locked_after_access() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    svc = _make_service(repo, has_lesson_access=True, module_locked=True)
    with pytest.raises(Forbidden) as exc_info:
        svc.start_module_quiz(
            _COURSE_ID, _MODULE_ID, cognito_sub=_STUDENT, role=_ROLE
        )
    assert exc_info.value.code == "module_locked"
    assert exc_info.value.status_code == 403


def test_submit_module_quiz_404_without_lesson_access() -> None:
    repo = MagicMock()
    svc = _make_service(repo, has_lesson_access=False, module_locked=True)
    with pytest.raises(NotFound):
        svc.submit_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT,
            role=_ROLE,
            attempt_id="attempt-1",
            answers={},
        )
    repo.get_attempt_with_binding_rows.assert_not_called()


def test_submit_module_quiz_403_module_locked_after_access() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    svc = _make_service(repo, has_lesson_access=True, module_locked=True)
    with pytest.raises(Forbidden) as exc_info:
        svc.submit_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT,
            role=_ROLE,
            attempt_id="attempt-1",
            answers={},
        )
    assert exc_info.value.code == "module_locked"
    repo.get_attempt_with_binding_rows.assert_not_called()
