"""Application service for question banks and module quizzes."""

from __future__ import annotations

from typing import Any, Optional

from services.common.errors import BadRequest, Conflict, NotFound
from services.question_banks.mcq_validation import (
    validate_correct_option_key,
    validate_draft_question_for_publish,
    validate_mcq_options_json,
)
from services.question_banks.ports import CourseMutateAuthorizerPort
from services.question_banks.rds_repo import QuestionBankRdsRepository


class QuestionBankService:
    def __init__(
        self,
        *,
        course_mutate_authorizer: CourseMutateAuthorizerPort,
        question_bank_repo: QuestionBankRdsRepository,
    ) -> None:
        self._authorizer = course_mutate_authorizer
        self._repo = question_bank_repo

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
