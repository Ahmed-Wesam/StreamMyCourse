"""RS-8 Slice 2: module quiz passPercent validation and persistence (service layer)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Forbidden, NotFound
from services.question_banks.gating import DEFAULT_MODULE_QUIZ_PASS_PERCENT
from services.question_banks.models import ModuleQuiz, QuestionBank
from services.question_banks.service import QuestionBankService

_COURSE_ID = "course-11111111-1111-1111-1111-111111111111"
_MODULE_ID = "module-22222222-2222-2222-2222-222222222222"
_BANK_ID = "33333333-3333-4333-8333-333333333333"
_QUIZ_ID = "quiz-55555555-5555-5555-5555-555555555555"
_COGNITO_SUB = "cognito-sub-actor"
_ROLE = "teacher"


def _make_service(authorizer: MagicMock, repo: MagicMock) -> QuestionBankService:
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


def _draft_bank() -> QuestionBank:
    return QuestionBank(
        id=_BANK_ID,
        courseId=_COURSE_ID,
        name="Bank",
        status="DRAFT",
        createdAt="",
        updatedAt="",
    )


def _module_quiz(*, pass_percent: int = DEFAULT_MODULE_QUIZ_PASS_PERCENT) -> ModuleQuiz:
    return ModuleQuiz(
        id=_QUIZ_ID,
        courseId=_COURSE_ID,
        moduleId=_MODULE_ID,
        questionBankId=_BANK_ID,
        servedCountN=None,
        passPercent=pass_percent,
        createdAt="2020-01-01T00:00:00Z",
        updatedAt="2020-01-01T00:00:00Z",
    )


def _wire_create_prereqs(repo: MagicMock) -> None:
    repo.get_question_bank_by_id.return_value = _draft_bank()
    repo.get_module_quiz_by_question_bank_id.return_value = None
    repo.insert_module_quiz.return_value = _QUIZ_ID


def test_create_module_quiz_omitted_pass_percent_stores_default() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    _wire_create_prereqs(repo)
    svc = _make_service(authorizer, repo)

    svc.create_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
        question_bank_id=_BANK_ID,
        pass_percent=None,
    )

    repo.insert_module_quiz.assert_called_once_with(
        course_id=_COURSE_ID,
        module_id=_MODULE_ID,
        question_bank_id=_BANK_ID,
        pass_percent=DEFAULT_MODULE_QUIZ_PASS_PERCENT,
    )


@pytest.mark.parametrize("bad_value", [0, 101])
def test_create_module_quiz_rejects_pass_percent_out_of_range(bad_value: int) -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    _wire_create_prereqs(repo)
    svc = _make_service(authorizer, repo)

    with pytest.raises(BadRequest, match="passPercent"):
        svc.create_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            question_bank_id=_BANK_ID,
            pass_percent=bad_value,
        )

    repo.insert_module_quiz.assert_not_called()


def test_create_module_quiz_rejects_non_int_pass_percent() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    _wire_create_prereqs(repo)
    svc = _make_service(authorizer, repo)

    with pytest.raises(BadRequest, match="passPercent"):
        svc.create_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            question_bank_id=_BANK_ID,
            pass_percent="70",  # type: ignore[arg-type]
        )

    repo.insert_module_quiz.assert_not_called()


def test_create_module_quiz_persists_custom_pass_percent() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    _wire_create_prereqs(repo)
    svc = _make_service(authorizer, repo)

    svc.create_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
        question_bank_id=_BANK_ID,
        pass_percent=85,
    )

    repo.insert_module_quiz.assert_called_once_with(
        course_id=_COURSE_ID,
        module_id=_MODULE_ID,
        question_bank_id=_BANK_ID,
        pass_percent=85,
    )


def test_patch_module_quiz_pass_percent_updates_for_publisher() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_module_quiz_by_module_id.return_value = _module_quiz()
    svc = _make_service(authorizer, repo)

    out = svc.patch_module_quiz_pass_percent(
        _COURSE_ID,
        _MODULE_ID,
        pass_percent=90,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )

    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.update_module_quiz_pass_percent.assert_called_once_with(
        course_id=_COURSE_ID,
        module_id=_MODULE_ID,
        pass_percent=90,
    )
    assert out["quizId"] == _QUIZ_ID
    assert out["passPercent"] == 90


def test_patch_module_quiz_forbidden_when_not_owner() -> None:
    authorizer = MagicMock()
    authorizer.ensure_course_mutable_by_actor.side_effect = Forbidden(
        "not allowed", code="forbidden"
    )
    repo = MagicMock()
    svc = _make_service(authorizer, repo)

    with pytest.raises(Forbidden, match="not allowed"):
        svc.patch_module_quiz_pass_percent(
            _COURSE_ID,
            _MODULE_ID,
            pass_percent=80,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )

    repo.get_module_quiz_by_module_id.assert_not_called()
    repo.update_module_quiz_pass_percent.assert_not_called()


@pytest.mark.parametrize("bad_value", [0, 101])
def test_patch_module_quiz_rejects_pass_percent_out_of_range(bad_value: int) -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_module_quiz_by_module_id.return_value = _module_quiz()
    svc = _make_service(authorizer, repo)

    with pytest.raises(BadRequest, match="passPercent"):
        svc.patch_module_quiz_pass_percent(
            _COURSE_ID,
            _MODULE_ID,
            pass_percent=bad_value,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )

    repo.update_module_quiz_pass_percent.assert_not_called()


def test_patch_module_quiz_not_found_when_no_quiz_row() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_module_quiz_by_module_id.return_value = None
    svc = _make_service(authorizer, repo)

    with pytest.raises(NotFound):
        svc.patch_module_quiz_pass_percent(
            _COURSE_ID,
            _MODULE_ID,
            pass_percent=75,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )

    repo.update_module_quiz_pass_percent.assert_not_called()


def test_list_module_quizzes_includes_pass_percent() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.list_module_quizzes_for_course.return_value = [_module_quiz(pass_percent=82)]
    svc = _make_service(authorizer, repo)

    out = svc.list_module_quizzes_for_course(
        _COURSE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )

    assert len(out) == 1
    assert out[0]["passPercent"] == 82
