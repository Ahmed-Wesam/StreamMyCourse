"""Lesson-notes deletion steps for course and user registries (DSQL-4)."""

from __future__ import annotations

from typing import Protocol

from services.course_deletion.catalog import split_deletion_parent_id
from services.course_deletion.registry import CourseDeletionRegistry

_NOTES_BATCH_ORDER = 100


class NotesDeletionRepo(Protocol):
    def delete_lesson_notes_for_user(self, user_sub: str) -> int: ...

    def delete_lesson_notes_for_course(self, course_id: str) -> int: ...

    def delete_lesson_notes_for_module(self, course_id: str, module_id: str) -> int: ...

    def delete_lesson_notes_for_lesson(self, course_id: str, lesson_id: str) -> int: ...


def register_lesson_note_deletion_steps(
    registry: CourseDeletionRegistry, repo: NotesDeletionRepo
) -> None:
    registry.register(
        name="lesson_notes_course",
        order=_NOTES_BATCH_ORDER,
        scope="course",
        run=lambda course_id: repo.delete_lesson_notes_for_course(course_id),
    )
    registry.register(
        name="lesson_notes_module",
        order=_NOTES_BATCH_ORDER,
        scope="module",
        run=lambda parent_id: repo.delete_lesson_notes_for_module(
            *split_deletion_parent_id(parent_id)
        ),
    )
    registry.register(
        name="lesson_notes_lesson",
        order=_NOTES_BATCH_ORDER,
        scope="lesson",
        run=lambda parent_id: repo.delete_lesson_notes_for_lesson(
            *split_deletion_parent_id(parent_id)
        ),
    )


__all__ = [
    "NotesDeletionRepo",
    "register_lesson_note_deletion_steps",
]
