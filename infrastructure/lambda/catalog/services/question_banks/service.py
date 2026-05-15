"""Application service for question banks and module quizzes."""

from __future__ import annotations

from typing import Optional

from services.common.errors import NotFound
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
