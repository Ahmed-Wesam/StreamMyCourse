"""Operator user deletion: learning records, purchases, then identity row."""

from __future__ import annotations

from services.lesson_notes.deletion import NotesDeletionRepo
from services.progress.deletion import ProgressDeletionRepo
from services.purchases.deletion import PurchaseDeletionRepo
from services.assignments.deletion import (
    AssignmentDeletionRepo,
    delete_assignment_children_for_user,
)
from services.question_banks.deletion import (
    QuestionBankDeletionRepo,
    delete_quiz_student_rows_for_user,
)
from services.user_deletion.identity import UserRowDeleter, register_identity_steps
from services.user_deletion.registry import UserDeletionRegistry

_LEARNING_ORDER = 100
_PURCHASES_ORDER = 200
_QUIZ_STUDENT_ORDER = 300
_ASSIGNMENT_CHILDREN_ORDER = 400


def register_operator_user_steps(
    registry: UserDeletionRegistry,
    profile_repo: UserRowDeleter,
    progress_repo: ProgressDeletionRepo,
    notes_repo: NotesDeletionRepo,
    purchase_repo: PurchaseDeletionRepo,
    quiz_repo: QuestionBankDeletionRepo,
    assignments_repo: AssignmentDeletionRepo,
) -> None:
    registry.register(
        name="lesson_progress",
        order=_LEARNING_ORDER,
        run=lambda user_sub: progress_repo.delete_lesson_progress_for_user(user_sub),
    )
    registry.register(
        name="lesson_notes",
        order=_LEARNING_ORDER,
        run=lambda user_sub: notes_repo.delete_lesson_notes_for_user(user_sub),
    )
    registry.register(
        name="learning_activity_days",
        order=_LEARNING_ORDER,
        run=lambda user_sub: progress_repo.delete_learning_activity_days_for_user(user_sub),
    )
    registry.register(
        name="purchases",
        order=_PURCHASES_ORDER,
        run=lambda user_sub: purchase_repo.delete_purchases_for_user(user_sub),
    )
    registry.register(
        name="quiz_student_rows",
        order=_QUIZ_STUDENT_ORDER,
        run=lambda user_sub: delete_quiz_student_rows_for_user(quiz_repo, user_sub),
    )
    registry.register(
        name="assignment_certificate_research_rows",
        order=_ASSIGNMENT_CHILDREN_ORDER,
        run=lambda user_sub: delete_assignment_children_for_user(
            assignments_repo, user_sub
        ),
    )
    register_identity_steps(registry, profile_repo)


__all__ = ["register_operator_user_steps"]
