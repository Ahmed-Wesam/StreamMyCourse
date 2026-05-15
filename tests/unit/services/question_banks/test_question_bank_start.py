"""Unit tests for ``QuestionBankService.start_module_quiz`` (QB-F slice 3)."""

from __future__ import annotations

import random
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

from services.common.errors import Conflict, NotFound
from services.question_banks.models import (
    BoundQuestion,
    ModuleQuiz,
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
    return [
        BoundQuestion(
            id=qid,
            promptText=f"prompt-{qid}",
            optionsJson='[{"key":"A","text":"choice A"}]',
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
    repo.get_binding_for_student.side_effect = [
        None,
        _binding(user_sub=_STUDENT_A, question_ids=ids),
    ]
    repo.list_published_question_ids.return_value = ["q1", "q2", "q3"]
    repo.list_student_bound_questions.return_value = _bound_questions(ids)
    svc = _make_start_service(repo)
    rng = random.Random(0)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=ids,
    ) as draw_mock:
        out = svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            rng=rng,
        )

    draw_mock.assert_called_once_with(["q1", "q2", "q3"], 2, rng)
    repo.insert_binding_with_questions.assert_called_once_with(
        module_quiz_id=_MQ_ID,
        course_id=_COURSE_ID,
        user_sub=_STUDENT_A,
        question_ids=ids,
    )
    assert out["servedCountN"] == 2
    assert len(out["questions"]) == 2
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
    repo.get_binding_for_student.return_value = _binding(
        user_sub=_STUDENT_A, question_ids=["q1", "q2"]
    )
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
    svc = _make_start_service(repo)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=["q1", "q2"],
    ):
        with pytest.raises(Conflict, match="could not be loaded after create"):
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
    repo.get_binding_for_student.return_value = binding
    repo.list_student_bound_questions.return_value = _bound_questions(ids)
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
    assert [q["id"] for q in first["questions"]] == ids
    assert [q["id"] for q in second["questions"]] == ids
    repo.insert_binding_with_questions.assert_not_called()
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
    repo.list_student_bound_questions.side_effect = [
        _bound_questions(["q-old-1", "q-old-2"]),
        _bound_questions(["q-new-3", "q-new-4"]),
    ]
    repo.get_binding_for_student.side_effect = [
        _binding(user_sub=_STUDENT_A, question_ids=["q-old-1", "q-old-2"]),
        None,
        _binding(user_sub=_STUDENT_B, question_ids=["q-new-3", "q-new-4"]),
    ]
    svc = _make_start_service(repo)
    rng_a = random.Random(1)
    rng_b = random.Random(2)

    with patch(
        "services.question_banks.service.draw_question_ids",
        side_effect=[["q-should-not-redraw"], ["q-new-3", "q-new-4"]],
    ) as draw_mock:
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
    assert [q["id"] for q in out_a["questions"]] == ["q-old-1", "q-old-2"]
    assert [q["id"] for q in out_b["questions"]] == ["q-new-3", "q-new-4"]
    repo.insert_binding_with_questions.assert_called_once()


def test_start_response_omits_correct_option_key() -> None:
    repo = MagicMock()
    _wire_start_gate(repo)
    ids = ["q1", "q2"]
    repo.get_binding_for_student.return_value = _binding(
        user_sub=_STUDENT_A, question_ids=ids
    )
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
    repo.get_binding_for_student.side_effect = [
        None,
        _binding(user_sub=_STUDENT_A, question_ids=["q1", "q2"]),
    ]
    repo.list_published_question_ids.return_value = ["q1", "q2", "q3"]
    repo.list_student_bound_questions.return_value = _bound_questions(["q1", "q2"])
    repo.insert_binding_with_questions.side_effect = Conflict("binding exists")
    svc = _make_start_service(repo)
    rng = random.Random(0)

    with patch(
        "services.question_banks.service.draw_question_ids",
        return_value=["q9", "q8"],
    ) as draw_mock:
        out = svc.start_module_quiz(
            _COURSE_ID,
            _MODULE_ID,
            cognito_sub=_STUDENT_A,
            role=_ROLE,
            rng=rng,
        )

    draw_mock.assert_called_once()
    assert [q["id"] for q in out["questions"]] == ["q1", "q2"]
    assert repo.get_binding_for_student.call_count == 2
