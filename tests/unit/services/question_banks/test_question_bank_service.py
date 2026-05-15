"""TDD Red (QB-B slice 1): ``QuestionBankService`` must authorize before RDS writes.

``services.question_banks.service`` is not implemented yet; importing ``QuestionBankService``
should fail until slice 2 adds the module/class.
"""

from __future__ import annotations

from typing import Any, List, Tuple
from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden
from services.question_banks.models import QuestionBank
from services.question_banks.service import QuestionBankService

_COURSE_ID = "course-11111111-1111-1111-1111-111111111111"
_MODULE_ID = "module-22222222-2222-2222-2222-222222222222"
_COGNITO_SUB = "cognito-sub-actor"
_ROLE = "teacher"


def _make_service(authorizer: MagicMock, repo: MagicMock) -> QuestionBankService:
    """Constructor shape for slice 2: explicit keyword ports."""
    return QuestionBankService(
        course_mutate_authorizer=authorizer,
        question_bank_repo=repo,
    )


def test_authorizer_called_before_insert_question_bank() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.insert_question_bank.return_value = "new-bank-id"

    events: List[Tuple[str, Any]] = []

    def on_auth(course_id: str, *, cognito_sub: str, role: str) -> None:
        events.append(("authorizer", (course_id, cognito_sub, role)))

    def on_insert(**kwargs: Any) -> str:
        events.append(("insert_question_bank", kwargs))
        return "new-bank-id"

    authorizer.ensure_course_mutable_by_actor.side_effect = on_auth
    repo.insert_question_bank.side_effect = on_insert

    svc = _make_service(authorizer, repo)
    result = svc.create_question_bank(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )

    assert result == "new-bank-id"
    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    assert events[0][0] == "authorizer"
    assert events[0][1] == (_COURSE_ID, _COGNITO_SUB, _ROLE)
    assert events[1][0] == "insert_question_bank"
    repo.insert_question_bank.assert_called_once()


def test_authorizer_called_before_insert_module_quiz() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.insert_module_quiz.return_value = "new-quiz-id"
    repo.get_question_bank_by_id.return_value = QuestionBank(
        id="optional-bank-id",
        courseId=_COURSE_ID,
        status="DRAFT",
        createdAt="",
        updatedAt="",
    )

    events: List[Tuple[str, Any]] = []

    def on_auth(course_id: str, *, cognito_sub: str, role: str) -> None:
        events.append(("authorizer", (course_id, cognito_sub, role)))

    def on_insert(**kwargs: Any) -> str:
        events.append(("insert_module_quiz", kwargs))
        return "new-quiz-id"

    authorizer.ensure_course_mutable_by_actor.side_effect = on_auth
    repo.insert_module_quiz.side_effect = on_insert

    svc = _make_service(authorizer, repo)
    result = svc.create_module_quiz(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
        question_bank_id="optional-bank-id",
    )

    assert result == "new-quiz-id"
    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    assert events[0][0] == "authorizer"
    assert events[0][1] == (_COURSE_ID, _COGNITO_SUB, _ROLE)
    assert events[1][0] == "insert_module_quiz"
    repo.insert_module_quiz.assert_called_once()


def test_forbidden_from_authorizer_propagates() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_mutable_by_actor.side_effect = Forbidden(
        "not allowed", code="forbidden"
    )

    svc = _make_service(authorizer, repo)

    with pytest.raises(Forbidden, match="not allowed"):
        svc.create_question_bank(_COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE)

    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.insert_question_bank.assert_not_called()
    repo.insert_module_quiz.assert_not_called()
