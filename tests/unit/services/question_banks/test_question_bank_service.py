"""Unit tests for ``QuestionBankService`` (authorization + domain rules)."""

from __future__ import annotations

from typing import Any, List, Tuple
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Conflict, Forbidden, NotFound
from services.question_banks.models import Question, QuestionBank
from services.question_banks.service import QuestionBankService

_COURSE_ID = "course-11111111-1111-1111-1111-111111111111"
_OTHER_COURSE_ID = "course-99999999-9999-9999-9999-999999999999"
_MODULE_ID = "module-22222222-2222-2222-2222-222222222222"
_BANK_ID = "33333333-3333-4333-8333-333333333333"
_QUESTION_ID = "quest-44444444-4444-4444-4444-444444444444"
_COGNITO_SUB = "cognito-sub-actor"
_ROLE = "teacher"

_MCQ_A = [{"key": "A", "text": "choice A"}]
_MCQ_B = [{"key": "B", "text": "choice B"}]
_MCQ_AB = [
    {"key": "A", "text": "choice A"},
    {"key": "B", "text": "choice B"},
]


def _draft_q(
    *,
    qid: str = "q1",
    correct: str | None = "A",
    options: Any | None = None,
) -> Question:
    opts = options if options is not None else (_MCQ_A if correct == "A" else _MCQ_B)
    return Question(
        id=qid,
        bankId=_BANK_ID,
        courseId=_COURSE_ID,
        status="DRAFT",
        correctOptionKey=correct,
        optionsJson=opts,
    )


def _draft_bank() -> QuestionBank:
    return QuestionBank(
        id=_BANK_ID,
        courseId=_COURSE_ID,
        name="Draft bank",
        status="DRAFT",
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


def _make_service(authorizer: MagicMock, repo: MagicMock) -> QuestionBankService:
    """Constructor shape: explicit keyword ports."""
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


def test_get_bank_for_course_returns_after_authz() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    svc = _make_service(authorizer, repo)
    out = svc.get_bank_for_course(
        _COURSE_ID,
        _BANK_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert out.status == "DRAFT"
    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.get_bank_for_course.assert_called_once_with(
        course_id=_COURSE_ID, bank_id=_BANK_ID
    )


def test_get_bank_for_course_not_found() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = None
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Question bank not found"):
        svc.get_bank_for_course(
            _COURSE_ID,
            _BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )


def test_get_bank_for_course_forbidden_before_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_mutable_by_actor.side_effect = Forbidden(
        "not allowed", code="forbidden"
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(Forbidden, match="not allowed"):
        svc.get_bank_for_course(
            _COURSE_ID,
            _BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.get_bank_for_course.assert_not_called()


def test_create_question_bank_trims_name_and_returns_payload() -> None:
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
        _COURSE_ID,
        name="  Final exam bank  ",
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )

    assert result == {"questionBankId": "new-bank-id", "name": "Final exam bank"}
    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    assert events[0][0] == "authorizer"
    assert events[0][1] == (_COURSE_ID, _COGNITO_SUB, _ROLE)
    assert events[1][0] == "insert_question_bank"
    repo.insert_question_bank.assert_called_once_with(
        course_id=_COURSE_ID, name="Final exam bank"
    )


def test_create_question_bank_rejects_blank_name_before_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    svc = _make_service(authorizer, repo)

    with pytest.raises(BadRequest, match="name"):
        svc.create_question_bank(
            _COURSE_ID,
            name="   ",
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )

    repo.insert_question_bank.assert_not_called()


def test_create_question_bank_rejects_long_name_before_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    svc = _make_service(authorizer, repo)

    with pytest.raises(BadRequest, match="80"):
        svc.create_question_bank(
            _COURSE_ID,
            name="x" * 81,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )

    repo.insert_question_bank.assert_not_called()


def test_authorizer_called_before_insert_module_quiz() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.insert_module_quiz.return_value = "new-quiz-id"
    repo.get_question_bank_by_id.return_value = QuestionBank(
        id=_BANK_ID,
        courseId=_COURSE_ID,
        name="Reusable bank",
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
        question_bank_id=_BANK_ID,
    )

    assert result == "new-quiz-id"
    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    assert events[0][0] == "authorizer"
    assert events[0][1] == (_COURSE_ID, _COGNITO_SUB, _ROLE)
    assert events[1][0] == "insert_module_quiz"
    repo.insert_module_quiz.assert_called_once()


def test_create_module_quiz_requires_question_bank_id() -> None:
    """Module quiz create rejects a missing ``questionBankId`` (BadRequest)."""
    authorizer = MagicMock()
    repo = MagicMock()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="questionBankId"):
        svc.create_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            question_bank_id=None,
        )
    repo.insert_module_quiz.assert_not_called()


def test_create_module_quiz_requires_non_blank_question_bank_id() -> None:
    """Whitespace-only ``questionBankId`` does not create a quiz row (BadRequest)."""
    authorizer = MagicMock()
    repo = MagicMock()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="questionBankId"):
        svc.create_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            question_bank_id="   ",
        )
    repo.insert_module_quiz.assert_not_called()


def test_create_module_quiz_rejects_question_bank_from_other_course() -> None:
    """Bank id must belong to ``course_id`` (BadRequest; no cross-course link)."""
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_question_bank_by_id.return_value = QuestionBank(
        id=_BANK_ID,
        courseId=_OTHER_COURSE_ID,
        name="Other course bank",
        status="DRAFT",
        createdAt="",
        updatedAt="",
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="course"):
        svc.create_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            question_bank_id=_BANK_ID,
        )
    repo.insert_module_quiz.assert_not_called()


def test_forbidden_from_authorizer_propagates() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_mutable_by_actor.side_effect = Forbidden(
        "not allowed", code="forbidden"
    )

    svc = _make_service(authorizer, repo)

    with pytest.raises(Forbidden, match="not allowed"):
        svc.create_question_bank(
            _COURSE_ID,
            name="Blocked bank",
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )

    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.insert_question_bank.assert_not_called()
    repo.insert_module_quiz.assert_not_called()


def test_publish_forbidden_before_any_repo_reads_or_writes() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_mutable_by_actor.side_effect = Forbidden(
        "not allowed", code="forbidden"
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(Forbidden, match="not allowed"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            2,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.get_bank_for_course.assert_not_called()
    repo.list_draft_questions.assert_not_called()
    repo.publish_bank_transaction.assert_not_called()


def test_publish_not_found_skips_list_and_transaction() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = None
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Question bank not found"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            1,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.get_bank_for_course.assert_called_once_with(
        course_id=_COURSE_ID, bank_id=_BANK_ID
    )
    repo.list_draft_questions.assert_not_called()
    repo.publish_bank_transaction.assert_not_called()


def test_publish_conflict_when_bank_not_draft_skips_list() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _published_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(Conflict, match="not in DRAFT"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            1,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.list_draft_questions.assert_not_called()
    repo.publish_bank_transaction.assert_not_called()


def test_publish_bad_request_when_n_less_than_one_skips_list() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="N must be at least 1"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            0,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.list_draft_questions.assert_not_called()
    repo.publish_bank_transaction.assert_not_called()


def test_publish_bad_request_zero_draft_questions() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    repo.list_draft_questions.return_value = []
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="no draft questions"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            1,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.publish_bank_transaction.assert_not_called()


def test_publish_bad_request_when_n_exceeds_draft_corpus() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    repo.list_draft_questions.return_value = [_draft_q(correct="A")]
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="N is greater than"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            2,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.publish_bank_transaction.assert_not_called()


def test_publish_bad_request_when_draft_lacks_designated_correct_answer() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    repo.list_draft_questions.return_value = [
        _draft_q(qid="q1", correct="A"),
        _draft_q(qid="q2", correct=None, options=_MCQ_A),
    ]
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="designated"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            2,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.publish_bank_transaction.assert_not_called()


def test_publish_bad_request_when_correct_option_is_blank() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    repo.list_draft_questions.return_value = [
        _draft_q(correct="   ", options=_MCQ_A),
    ]
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="designated"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            1,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.publish_bank_transaction.assert_not_called()


def test_publish_authorizer_runs_before_repo_reads() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    repo.list_draft_questions.return_value = [
        _draft_q(qid="q1", correct="A"),
        _draft_q(qid="q2", correct="B", options=_MCQ_B),
    ]
    events: List[Tuple[str, Any]] = []

    def on_auth(course_id: str, *, cognito_sub: str, role: str) -> None:
        events.append(("authorizer", (course_id, cognito_sub, role)))

    def on_get_bank(**kwargs: Any) -> QuestionBank:
        events.append(("get_bank_for_course", kwargs))
        return _draft_bank()

    def on_list(**kwargs: Any) -> List[Question]:
        events.append(("list_draft_questions", kwargs))
        return repo.list_draft_questions.return_value

    def on_publish(**kwargs: Any) -> None:
        events.append(("publish_bank_transaction", kwargs))

    authorizer.ensure_course_mutable_by_actor.side_effect = on_auth
    repo.get_bank_for_course.side_effect = on_get_bank
    repo.list_draft_questions.side_effect = on_list
    repo.publish_bank_transaction.side_effect = on_publish

    svc = _make_service(authorizer, repo)
    svc.publish_question_bank(
        _COURSE_ID,
        _BANK_ID,
        _MODULE_ID,
        2,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert events[0][0] == "authorizer"
    assert events[1][0] == "get_bank_for_course"
    assert events[2][0] == "list_draft_questions"
    assert events[3][0] == "publish_bank_transaction"
    repo.publish_bank_transaction.assert_called_once_with(
        course_id=_COURSE_ID,
        bank_id=_BANK_ID,
        module_id=_MODULE_ID,
        n=2,
    )


def test_add_published_question_rejects_draft_bank() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="bank is published"):
        svc.add_published_question(
            _COURSE_ID,
            _BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            prompt_text="Pick one",
            options_json=_MCQ_AB,
            correct_option_key="A",
        )
    repo.insert_published_question.assert_not_called()


def test_add_published_question_inserts_when_bank_published() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _published_bank()
    repo.insert_published_question.return_value = "new-published-q"
    svc = _make_service(authorizer, repo)
    out = svc.add_published_question(
        _COURSE_ID,
        _BANK_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
        prompt_text="  What is 2+2?  ",
        options_json=_MCQ_AB,
        correct_option_key="B",
    )
    assert out == "new-published-q"
    repo.insert_published_question.assert_called_once_with(
        course_id=_COURSE_ID,
        bank_id=_BANK_ID,
        prompt_text="What is 2+2?",
        options_json=_MCQ_AB,
        correct_option_key="B",
    )


def test_add_published_question_rejects_blank_prompt() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _published_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="promptText"):
        svc.add_published_question(
            _COURSE_ID,
            _BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            prompt_text="   ",
            options_json=_MCQ_AB,
            correct_option_key="A",
        )
    repo.insert_published_question.assert_not_called()


def test_add_published_question_rejects_empty_options() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _published_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="optionsJson"):
        svc.add_published_question(
            _COURSE_ID,
            _BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            prompt_text="Q?",
            options_json=[],
            correct_option_key="A",
        )
    repo.insert_published_question.assert_not_called()


def test_add_published_question_rejects_correct_key_not_in_options() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _published_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="correctOptionKey"):
        svc.add_published_question(
            _COURSE_ID,
            _BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            prompt_text="Q?",
            options_json=_MCQ_A,
            correct_option_key="Z",
        )
    repo.insert_published_question.assert_not_called()


def test_add_published_question_rejects_empty_correct_key() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _published_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="correctOptionKey"):
        svc.add_published_question(
            _COURSE_ID,
            _BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
            prompt_text="Q?",
            options_json=_MCQ_AB,
            correct_option_key="   ",
        )
    repo.insert_published_question.assert_not_called()


def test_update_question_conflict_when_published_skips_repo_update() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_question_by_id.return_value = Question(
        id=_QUESTION_ID,
        bankId=_BANK_ID,
        courseId=_COURSE_ID,
        status="PUBLISHED",
        correctOptionKey="A",
        optionsJson=_MCQ_A,
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(Conflict, match="cannot be updated"):
        svc.update_question(
            _COURSE_ID,
            _BANK_ID,
            _QUESTION_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.update_question.assert_not_called()


def test_delete_question_conflict_when_published_skips_repo_delete() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_question_by_id.return_value = Question(
        id=_QUESTION_ID,
        bankId=_BANK_ID,
        courseId=_COURSE_ID,
        status="PUBLISHED",
        correctOptionKey="A",
        optionsJson=_MCQ_A,
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(Conflict, match="cannot be deleted"):
        svc.delete_question(
            _COURSE_ID,
            _BANK_ID,
            _QUESTION_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.delete_question.assert_not_called()


def test_create_draft_question_forbidden_before_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_mutable_by_actor.side_effect = Forbidden(
        "not allowed", code="forbidden"
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(Forbidden, match="not allowed"):
        svc.create_draft_question(
            _COURSE_ID,
            _BANK_ID,
            prompt_text="Q?",
            options_json=[{"key": "A", "text": "a"}],
            correct_option_key=None,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.get_bank_for_course.assert_not_called()
    repo.insert_draft_question.assert_not_called()


def test_create_draft_question_not_found_skips_insert() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = None
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Question bank not found"):
        svc.create_draft_question(
            _COURSE_ID,
            _BANK_ID,
            prompt_text="Q?",
            options_json=[],
            correct_option_key=None,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.insert_draft_question.assert_not_called()


def test_create_draft_question_rejects_published_bank() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _published_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="DRAFT status"):
        svc.create_draft_question(
            _COURSE_ID,
            _BANK_ID,
            prompt_text="Q?",
            options_json=_MCQ_A,
            correct_option_key="A",
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.insert_draft_question.assert_not_called()


def test_create_draft_question_rejects_blank_prompt() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="promptText"):
        svc.create_draft_question(
            _COURSE_ID,
            _BANK_ID,
            prompt_text="   ",
            options_json=_MCQ_A,
            correct_option_key=None,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.insert_draft_question.assert_not_called()


def test_create_draft_question_inserts_when_bank_draft() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    repo.insert_draft_question.return_value = "new-q-id"
    svc = _make_service(authorizer, repo)
    out = svc.create_draft_question(
        _COURSE_ID,
        _BANK_ID,
        prompt_text="  What?  ",
        options_json=_MCQ_A,
        correct_option_key="A",
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert out == "new-q-id"
    repo.insert_draft_question.assert_called_once_with(
        course_id=_COURSE_ID,
        bank_id=_BANK_ID,
        prompt_text="What?",
        options_json=_MCQ_A,
        correct_option_key="A",
    )


def test_publish_bad_request_when_correct_key_not_in_options() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    repo.list_draft_questions.return_value = [
        _draft_q(correct="Z", options=_MCQ_A),
    ]
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="correctOptionKey"):
        svc.publish_question_bank(
            _COURSE_ID,
            _BANK_ID,
            _MODULE_ID,
            1,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.publish_bank_transaction.assert_not_called()


def test_create_draft_question_rejects_empty_options() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="optionsJson"):
        svc.create_draft_question(
            _COURSE_ID,
            _BANK_ID,
            prompt_text="Q?",
            options_json=[],
            correct_option_key=None,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.insert_draft_question.assert_not_called()


def test_create_draft_question_rejects_correct_key_not_in_options() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    svc = _make_service(authorizer, repo)
    with pytest.raises(BadRequest, match="correctOptionKey"):
        svc.create_draft_question(
            _COURSE_ID,
            _BANK_ID,
            prompt_text="Q?",
            options_json=_MCQ_A,
            correct_option_key="Z",
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.insert_draft_question.assert_not_called()


def test_update_question_passes_fields_for_draft() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_question_by_id.return_value = _draft_q(
        qid=_QUESTION_ID, correct="A", options=_MCQ_A
    )
    svc = _make_service(authorizer, repo)
    svc.update_question(
        _COURSE_ID,
        _BANK_ID,
        _QUESTION_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
        prompt_text="Updated?",
        options_json=_MCQ_B,
        correct_option_key="B",
    )
    repo.update_question.assert_called_once_with(
        course_id=_COURSE_ID,
        bank_id=_BANK_ID,
        question_id=_QUESTION_ID,
        prompt_text="Updated?",
        options_json=_MCQ_B,
        correct_option_key="B",
    )


def test_update_question_not_found_when_course_mismatch() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_question_by_id.return_value = Question(
        id=_QUESTION_ID,
        bankId=_BANK_ID,
        courseId="other-course",
        status="DRAFT",
        correctOptionKey="A",
        optionsJson=_MCQ_A,
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Question not found"):
        svc.update_question(
            _COURSE_ID,
            _BANK_ID,
            _QUESTION_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )


# Valid UUIDs required by ``list_questions_for_publisher`` (``UUID`` gate) and
# ``ensure_publisher_question_bank_read`` (``_is_valid_uuid`` on course id).
_READ_COURSE_ID = "11111111-1111-4111-8111-111111111111"
_READ_BANK_ID = "22222222-2222-4222-8222-222222222222"
_READ_Q_ID = "33333333-3333-4333-8333-333333333333"


def test_list_question_banks_calls_publisher_read_scope_then_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.list_question_banks_for_course.return_value = []
    svc = _make_service(authorizer, repo)
    out = svc.list_question_banks_for_course(
        _READ_COURSE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert out == []
    authorizer.ensure_course_publisher_read_scope.assert_called_once_with(
        _READ_COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.list_question_banks_for_course.assert_called_once_with(
        course_id=_READ_COURSE_ID
    )


def test_list_question_banks_maps_repo_rows() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.list_question_banks_for_course.return_value = [
        QuestionBank(
            id=_READ_BANK_ID,
            courseId=_READ_COURSE_ID,
            name="Midterm bank",
            status="DRAFT",
            createdAt="2026-01-01T00:00:00Z",
            updatedAt="2026-01-02T00:00:00Z",
        )
    ]
    svc = _make_service(authorizer, repo)
    out = svc.list_question_banks_for_course(
        _READ_COURSE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert out == [
        {
            "questionBankId": _READ_BANK_ID,
            "name": "Midterm bank",
            "status": "DRAFT",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
        }
    ]


def test_list_question_banks_uses_legacy_name_fallback() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.list_question_banks_for_course.return_value = [
        QuestionBank(
            id=_READ_BANK_ID,
            courseId=_READ_COURSE_ID,
            name=None,
            status="DRAFT",
            createdAt="2026-01-01T00:00:00Z",
            updatedAt="2026-01-02T00:00:00Z",
        )
    ]
    svc = _make_service(authorizer, repo)
    out = svc.list_question_banks_for_course(
        _READ_COURSE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert out[0]["name"] == f"Question bank {_READ_BANK_ID[:8]}"


@pytest.mark.parametrize("bank", [_draft_bank(), _published_bank()])
def test_rename_question_bank_updates_draft_and_published(bank: QuestionBank) -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = bank
    svc = _make_service(authorizer, repo)

    out = svc.rename_question_bank(
        _COURSE_ID,
        _BANK_ID,
        name="  Renamed bank  ",
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )

    assert out == {"questionBankId": _BANK_ID, "name": "Renamed bank"}
    authorizer.ensure_course_mutable_by_actor.assert_called_once_with(
        _COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.get_bank_for_course.assert_called_once_with(
        course_id=_COURSE_ID, bank_id=_BANK_ID
    )
    repo.update_question_bank_name.assert_called_once_with(
        course_id=_COURSE_ID, bank_id=_BANK_ID, name="Renamed bank"
    )


def test_rename_question_bank_not_found_when_wrong_course() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = None
    svc = _make_service(authorizer, repo)

    with pytest.raises(NotFound, match="Question bank not found"):
        svc.rename_question_bank(
            _COURSE_ID,
            _BANK_ID,
            name="New name",
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )

    repo.update_question_bank_name.assert_not_called()


def test_rename_question_bank_scope_failure_before_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_mutable_by_actor.side_effect = NotFound(
        "Course not found", code="not_found"
    )
    svc = _make_service(authorizer, repo)

    with pytest.raises(NotFound, match="Course not found"):
        svc.rename_question_bank(
            _COURSE_ID,
            _BANK_ID,
            name="New name",
            cognito_sub=_COGNITO_SUB,
            role="student",
        )

    repo.get_bank_for_course.assert_not_called()
    repo.update_question_bank_name.assert_not_called()


def test_rename_question_bank_rejects_invalid_names() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = _draft_bank()
    svc = _make_service(authorizer, repo)

    for bad_name in ("", "   ", "x" * 81):
        with pytest.raises(BadRequest, match="name"):
            svc.rename_question_bank(
                _COURSE_ID,
                _BANK_ID,
                name=bad_name,
                cognito_sub=_COGNITO_SUB,
                role=_ROLE,
            )

    repo.update_question_bank_name.assert_not_called()


def test_list_question_banks_not_found_when_publisher_scope_denies() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_publisher_read_scope.side_effect = NotFound(
        "Course not found", code="not_found"
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Course not found"):
        svc.list_question_banks_for_course(
            _READ_COURSE_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.list_question_banks_for_course.assert_not_called()


def test_list_questions_for_publisher_success_options_json_parsed() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = QuestionBank(
        id=_READ_BANK_ID,
        courseId=_READ_COURSE_ID,
        name="Question bank",
        status="DRAFT",
        createdAt="",
        updatedAt="",
    )
    repo.list_questions_for_course_bank.return_value = [
        Question(
            id=_READ_Q_ID,
            bankId=_READ_BANK_ID,
            courseId=_READ_COURSE_ID,
            status="DRAFT",
            correctOptionKey="A",
            promptText="Hi?",
            optionsJson='[{"key": "A", "text": "one"}]',
            createdAt="",
            updatedAt="",
        )
    ]
    svc = _make_service(authorizer, repo)
    out = svc.list_questions_for_publisher(
        _READ_COURSE_ID,
        _READ_BANK_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert len(out) == 1
    assert out[0]["questionId"] == _READ_Q_ID
    assert out[0]["status"] == "DRAFT"
    assert out[0]["promptText"] == "Hi?"
    assert out[0]["correctOptionKey"] == "A"
    assert out[0]["optionsJson"] == [{"key": "A", "text": "one"}]
    authorizer.ensure_course_publisher_read_scope.assert_called_once_with(
        _READ_COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.get_bank_for_course.assert_called_once_with(
        course_id=_READ_COURSE_ID, bank_id=_READ_BANK_ID
    )
    repo.list_questions_for_course_bank.assert_called_once_with(
        course_id=_READ_COURSE_ID, bank_id=_READ_BANK_ID
    )


def test_list_questions_for_publisher_bank_not_found() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    repo.get_bank_for_course.return_value = None
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Question bank not found"):
        svc.list_questions_for_publisher(
            _READ_COURSE_ID,
            _READ_BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.list_questions_for_course_bank.assert_not_called()


def test_list_questions_for_publisher_invalid_bank_id() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Question bank not found"):
        svc.list_questions_for_publisher(
            _READ_COURSE_ID,
            "not-a-uuid",
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.get_bank_for_course.assert_not_called()


def test_list_questions_for_publisher_scope_failure_before_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_publisher_read_scope.side_effect = NotFound(
        "Course not found", code="not_found"
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound):
        svc.list_questions_for_publisher(
            _READ_COURSE_ID,
            _READ_BANK_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.get_bank_for_course.assert_not_called()


def test_list_module_quizzes_for_course_calls_publisher_read_scope_then_repo() -> None:
    """QB-L Plan 2: ``list_module_quizzes_for_course`` delegates to repo only after publisher read scope."""
    authorizer = MagicMock()
    repo = MagicMock()
    repo.list_module_quizzes_for_course.return_value = []
    svc = _make_service(authorizer, repo)
    out = svc.list_module_quizzes_for_course(
        _READ_COURSE_ID,
        cognito_sub=_COGNITO_SUB,
        role=_ROLE,
    )
    assert out == []
    authorizer.ensure_course_publisher_read_scope.assert_called_once_with(
        _READ_COURSE_ID, cognito_sub=_COGNITO_SUB, role=_ROLE
    )
    repo.list_module_quizzes_for_course.assert_called_once_with(course_id=_READ_COURSE_ID)


def test_list_module_quizzes_for_course_scope_failure_before_repo() -> None:
    authorizer = MagicMock()
    repo = MagicMock()
    authorizer.ensure_course_publisher_read_scope.side_effect = NotFound(
        "Course not found", code="not_found"
    )
    svc = _make_service(authorizer, repo)
    with pytest.raises(NotFound, match="Course not found"):
        svc.list_module_quizzes_for_course(
            _READ_COURSE_ID,
            cognito_sub=_COGNITO_SUB,
            role=_ROLE,
        )
    repo.list_module_quizzes_for_course.assert_not_called()
