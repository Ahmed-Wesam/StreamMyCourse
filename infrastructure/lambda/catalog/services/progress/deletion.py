"""Learning-record deletion steps for course and user registries (DSQL-4)."""

from __future__ import annotations

from typing import Protocol

from services.course_deletion.catalog import split_deletion_parent_id
from services.course_deletion.registry import CourseDeletionRegistry

_LEARNING_BATCH_ORDER = 100


class ProgressDeletionRepo(Protocol):
    def delete_lesson_progress_for_user(self, user_sub: str) -> int: ...

    def delete_learning_activity_days_for_user(self, user_sub: str) -> int: ...

    def delete_lesson_progress_for_course(self, course_id: str) -> int: ...

    def delete_lesson_progress_for_module(self, course_id: str, module_id: str) -> int: ...

    def delete_lesson_progress_for_lesson(self, course_id: str, lesson_id: str) -> int: ...


def register_progress_deletion_steps(
    registry: CourseDeletionRegistry, repo: ProgressDeletionRepo
) -> None:
    registry.register(
        name="lesson_progress_course",
        order=_LEARNING_BATCH_ORDER,
        scope="course",
        run=lambda course_id: repo.delete_lesson_progress_for_course(course_id),
    )
    registry.register(
        name="lesson_progress_module",
        order=_LEARNING_BATCH_ORDER,
        scope="module",
        run=lambda parent_id: repo.delete_lesson_progress_for_module(
            *split_deletion_parent_id(parent_id)
        ),
    )
    registry.register(
        name="lesson_progress_lesson",
        order=_LEARNING_BATCH_ORDER,
        scope="lesson",
        run=lambda parent_id: repo.delete_lesson_progress_for_lesson(
            *split_deletion_parent_id(parent_id)
        ),
    )


__all__ = [
    "ProgressDeletionRepo",
    "register_progress_deletion_steps",
]
