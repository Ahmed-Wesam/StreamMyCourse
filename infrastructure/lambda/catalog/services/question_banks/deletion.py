"""Question-bank and module-quiz deletion steps (DSQL-6 S5)."""

from __future__ import annotations

from typing import Protocol

from services.course_deletion.catalog import split_deletion_parent_id
from services.course_deletion.registry import CourseDeletionRegistry

_QUIZ_DELETION_ORDER = 300


class QuestionBankDeletionRepo(Protocol):
    def delete_module_quiz_attempt_submissions_for_user(self, user_sub: str) -> int: ...

    def delete_module_quiz_attempts_for_user(self, user_sub: str) -> int: ...

    def delete_binding_questions_for_user(self, user_sub: str) -> int: ...

    def delete_bindings_for_user(self, user_sub: str) -> int: ...

    def delete_module_quiz_attempt_submissions_for_course(self, course_id: str) -> int: ...

    def delete_module_quiz_attempts_for_course(self, course_id: str) -> int: ...

    def delete_binding_questions_for_course(self, course_id: str) -> int: ...

    def delete_bindings_for_course(self, course_id: str) -> int: ...

    def delete_module_quizzes_for_course(self, course_id: str) -> int: ...

    def delete_questions_for_course(self, course_id: str) -> int: ...

    def delete_question_banks_for_course(self, course_id: str) -> int: ...

    def delete_module_quiz_attempt_submissions_for_module(
        self, course_id: str, module_id: str
    ) -> int: ...

    def delete_module_quiz_attempts_for_module(self, course_id: str, module_id: str) -> int: ...

    def delete_binding_questions_for_module(self, course_id: str, module_id: str) -> int: ...

    def delete_bindings_for_module(self, course_id: str, module_id: str) -> int: ...


def delete_quiz_student_rows_for_user(repo: QuestionBankDeletionRepo, user_sub: str) -> None:
    repo.delete_module_quiz_attempt_submissions_for_user(user_sub)
    repo.delete_module_quiz_attempts_for_user(user_sub)
    repo.delete_binding_questions_for_user(user_sub)
    repo.delete_bindings_for_user(user_sub)


def delete_quiz_student_rows_for_course(repo: QuestionBankDeletionRepo, course_id: str) -> None:
    repo.delete_module_quiz_attempt_submissions_for_course(course_id)
    repo.delete_module_quiz_attempts_for_course(course_id)
    repo.delete_binding_questions_for_course(course_id)
    repo.delete_bindings_for_course(course_id)


def delete_quiz_student_rows_for_module(
    repo: QuestionBankDeletionRepo, course_id: str, module_id: str
) -> None:
    repo.delete_module_quiz_attempt_submissions_for_module(course_id, module_id)
    repo.delete_module_quiz_attempts_for_module(course_id, module_id)
    repo.delete_binding_questions_for_module(course_id, module_id)
    repo.delete_bindings_for_module(course_id, module_id)


def delete_quiz_course_content(repo: QuestionBankDeletionRepo, course_id: str) -> None:
    delete_quiz_student_rows_for_course(repo, course_id)
    repo.delete_module_quizzes_for_course(course_id)
    repo.delete_questions_for_course(course_id)
    repo.delete_question_banks_for_course(course_id)


def register_question_bank_deletion_steps(
    registry: CourseDeletionRegistry, repo: QuestionBankDeletionRepo
) -> None:
    registry.register(
        name="quiz_rows_course",
        order=_QUIZ_DELETION_ORDER,
        scope="course",
        run=lambda course_id: delete_quiz_course_content(repo, course_id),
    )
    registry.register(
        name="quiz_rows_module",
        order=_QUIZ_DELETION_ORDER,
        scope="module",
        run=lambda parent_id: delete_quiz_student_rows_for_module(
            repo, *split_deletion_parent_id(parent_id)
        ),
    )


__all__ = [
    "QuestionBankDeletionRepo",
    "delete_quiz_course_content",
    "delete_quiz_student_rows_for_module",
    "delete_quiz_student_rows_for_user",
    "register_question_bank_deletion_steps",
]
