"""Operator user deletion: learning records, purchases, then identity row."""

from __future__ import annotations

from services.lesson_notes.deletion import NotesDeletionRepo
from services.progress.deletion import ProgressDeletionRepo
from services.purchases.deletion import PurchaseDeletionRepo
from services.user_deletion.identity import UserRowDeleter, register_identity_steps
from services.user_deletion.registry import UserDeletionRegistry

_LEARNING_ORDER = 100
_PURCHASES_ORDER = 200


def register_operator_user_steps(
    registry: UserDeletionRegistry,
    profile_repo: UserRowDeleter,
    progress_repo: ProgressDeletionRepo,
    notes_repo: NotesDeletionRepo,
    purchase_repo: PurchaseDeletionRepo,
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
    register_identity_steps(registry, profile_repo)


__all__ = ["register_operator_user_steps"]
