"""Application service for question banks and module quizzes."""

from __future__ import annotations

import json
import random
from typing import Any, Optional

from services.common.errors import BadRequest, Conflict, NotFound
from services.question_banks.binding_draw import draw_question_ids
from services.question_banks.mcq_validation import (
    validate_correct_option_key,
    validate_draft_question_for_publish,
    validate_mcq_options_json,
)
from services.question_banks.models import ModuleQuiz, StudentModuleQuizBinding
from services.question_banks.ports import (
    CourseMutateAuthorizerPort,
    CourseReadPort,
    StudentLessonAccessPort,
)
from services.question_banks.rds_repo import QuestionBankRdsRepository


class QuestionBankService:
    def __init__(
        self,
        *,
        course_mutate_authorizer: CourseMutateAuthorizerPort,
        question_bank_repo: QuestionBankRdsRepository,
        student_lesson_access: StudentLessonAccessPort,
        course_read: CourseReadPort,
    ) -> None:
        self._authorizer = course_mutate_authorizer
        self._repo = question_bank_repo
        self._lesson_access = student_lesson_access
        self._course_read = course_read

    def start_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
        rng: random.Random | None = None,
    ) -> dict[str, Any]:
        module_quiz = self._resolve_startable_module_quiz(
            course_id, module_id, cognito_sub=cognito_sub, role=role
        )
        user_sub = cognito_sub.strip()
        binding = self._repo.get_binding_for_student(
            module_quiz_id=module_quiz.id, user_sub=user_sub
        )
        if binding is None:
            binding = self._create_binding_for_student(
                module_quiz,
                course_id=course_id,
                user_sub=user_sub,
                rng=rng,
            )
        return self._build_module_quiz_start_response(module_quiz, binding)

    def _resolve_startable_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> ModuleQuiz:
        status = self._course_read.get_course_status(course_id)
        if status != "PUBLISHED":
            raise NotFound("Module quiz not available")
        if not self._lesson_access.viewer_has_lesson_access(
            course_id, cognito_sub, role
        ):
            raise NotFound("Module quiz not available")
        module_quiz = self._repo.get_module_quiz_by_module_id(module_id=module_id)
        if module_quiz is None or module_quiz.courseId != course_id:
            raise NotFound("Module quiz not available")
        bank_id = module_quiz.questionBankId
        served_n = module_quiz.servedCountN
        if not bank_id or served_n is None or served_n < 1:
            raise NotFound("Module quiz not available")
        bank = self._repo.get_question_bank_by_id(bank_id=bank_id)
        if (
            bank is None
            or bank.courseId != course_id
            or bank.status != "PUBLISHED"
        ):
            raise NotFound("Module quiz not available")
        return module_quiz

    def _create_binding_for_student(
        self,
        module_quiz: ModuleQuiz,
        *,
        course_id: str,
        user_sub: str,
        rng: random.Random | None,
    ) -> StudentModuleQuizBinding:
        bank_id = module_quiz.questionBankId
        assert bank_id is not None
        served_n = module_quiz.servedCountN
        assert served_n is not None and served_n >= 1
        published_ids = self._repo.list_published_question_ids(
            course_id=course_id, bank_id=bank_id
        )
        draw_rng = rng if rng is not None else random.Random()
        try:
            drawn_ids = draw_question_ids(published_ids, served_n, draw_rng)
        except ValueError as exc:
            raise Conflict(str(exc)) from exc
        try:
            self._repo.insert_binding_with_questions(
                module_quiz_id=module_quiz.id,
                course_id=course_id,
                user_sub=user_sub,
                question_ids=drawn_ids,
            )
        except Conflict:
            binding = self._repo.get_binding_for_student(
                module_quiz_id=module_quiz.id, user_sub=user_sub
            )
            if binding is None:
                raise
            return binding
        binding = self._repo.get_binding_for_student(
            module_quiz_id=module_quiz.id, user_sub=user_sub
        )
        if binding is None:
            raise Conflict("Module quiz binding could not be loaded after create")
        return binding

    def _build_module_quiz_start_response(
        self,
        module_quiz: ModuleQuiz,
        binding: StudentModuleQuizBinding,
    ) -> dict[str, Any]:
        served_n = module_quiz.servedCountN
        assert served_n is not None
        if len(binding.questionIds) != served_n:
            raise Conflict("Module quiz binding is incomplete")
        rows = self._repo.list_student_bound_questions(
            course_id=binding.courseId,
            question_ids=binding.questionIds,
        )
        questions = [
            {
                "id": row.id,
                "promptText": row.promptText,
                "optionsJson": _parse_options_json(row.optionsJson),
            }
            for row in rows
        ]
        if len(questions) != served_n:
            raise Conflict("Module quiz questions could not be loaded")
        return {
            "moduleQuizId": module_quiz.id,
            "moduleId": module_quiz.moduleId,
            "servedCountN": served_n,
            "questions": questions,
        }

    def create_question_bank(
        self, course_id: str, *, cognito_sub: str, role: str
    ) -> str:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        return self._repo.insert_question_bank(course_id=course_id)

    def create_module_quiz(
        self,
        course_id: str,
        module_id: str,
        *,
        cognito_sub: str,
        role: str,
        question_bank_id: str | None = None,
    ) -> str:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        resolved: Optional[str] = None
        bank_ref = (question_bank_id or "").strip()
        if bank_ref:
            bank = self._repo.get_question_bank_by_id(bank_id=bank_ref)
            if bank is None or bank.courseId != course_id:
                raise NotFound("Question bank not found for this course")
            resolved = bank_ref
        return self._repo.insert_module_quiz(
            course_id=course_id,
            module_id=module_id,
            question_bank_id=resolved,
        )

    def create_draft_question(
        self,
        course_id: str,
        bank_id: str,
        *,
        prompt_text: str,
        options_json: Any,
        correct_option_key: str | None,
        cognito_sub: str,
        role: str,
    ) -> str:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        if bank.status != "DRAFT":
            raise BadRequest(
                "Draft questions can only be created when the bank is in DRAFT status"
            )
        text = (prompt_text or "").strip()
        if not text:
            raise BadRequest("promptText must not be empty")
        validate_mcq_options_json(options_json)
        validate_correct_option_key(
            correct_option_key, options_json=options_json
        )
        return self._repo.insert_draft_question(
            course_id=course_id,
            bank_id=bank_id,
            prompt_text=text,
            options_json=options_json,
            correct_option_key=correct_option_key,
        )

    def publish_question_bank(
        self,
        course_id: str,
        bank_id: str,
        module_id: str,
        n: int,
        *,
        cognito_sub: str,
        role: str,
    ) -> None:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        if bank.status != "DRAFT":
            raise Conflict("Question bank is not in DRAFT status")
        if n < 1:
            raise BadRequest("N must be at least 1")
        drafts = self._repo.list_draft_questions(bank_id=bank_id)
        if len(drafts) == 0:
            raise BadRequest("Cannot publish: question bank has no draft questions")
        if n > len(drafts):
            raise BadRequest(
                "Cannot publish: N is greater than the number of draft questions"
            )
        for q in drafts:
            validate_draft_question_for_publish(
                correct_option_key=q.correctOptionKey,
                options_json=q.optionsJson,
            )
        self._repo.publish_bank_transaction(
            course_id=course_id,
            bank_id=bank_id,
            module_id=module_id,
            n=n,
        )

    def add_published_question(
        self,
        course_id: str,
        bank_id: str,
        *,
        cognito_sub: str,
        role: str,
        correct_option_key: str,
    ) -> str:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        bank = self._repo.get_bank_for_course(course_id=course_id, bank_id=bank_id)
        if bank is None:
            raise NotFound("Question bank not found for this course")
        if bank.status != "PUBLISHED":
            raise BadRequest(
                "Published questions can only be added when the bank is published"
            )
        key = (correct_option_key or "").strip()
        if not key:
            raise BadRequest("correct_option_key is required")
        return self._repo.insert_published_question(
            course_id=course_id,
            bank_id=bank_id,
            correct_option_key=key,
        )

    def update_question(
        self,
        course_id: str,
        bank_id: str,
        question_id: str,
        *,
        cognito_sub: str,
        role: str,
        prompt_text: str | None = None,
        options_json: Any = None,
        correct_option_key: str | None = None,
    ) -> None:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        existing = self._repo.get_question_by_id(
            bank_id=bank_id, question_id=question_id
        )
        if existing is None or existing.courseId != course_id:
            raise NotFound("Question not found for this bank")
        if existing.status == "PUBLISHED":
            raise Conflict("Published questions cannot be updated")
        merged_options = (
            options_json if options_json is not None else existing.optionsJson
        )
        merged_correct = (
            correct_option_key
            if correct_option_key is not None
            else existing.correctOptionKey
        )
        if options_json is not None:
            validate_mcq_options_json(options_json)
        if options_json is not None or correct_option_key is not None:
            validate_correct_option_key(merged_correct, options_json=merged_options)
        self._repo.update_question(
            course_id=course_id,
            bank_id=bank_id,
            question_id=question_id,
            prompt_text=prompt_text,
            options_json=options_json,
            correct_option_key=correct_option_key,
        )

    def delete_question(
        self,
        course_id: str,
        bank_id: str,
        question_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> None:
        self._authorizer.ensure_course_mutable_by_actor(
            course_id, cognito_sub=cognito_sub, role=role
        )
        existing = self._repo.get_question_by_id(
            bank_id=bank_id, question_id=question_id
        )
        if existing is None or existing.courseId != course_id:
            raise NotFound("Question not found for this bank")
        if existing.status == "PUBLISHED":
            raise Conflict("Published questions cannot be deleted")
        self._repo.delete_question(
            course_id=course_id,
            bank_id=bank_id,
            question_id=question_id,
        )


def _parse_options_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw
