"""Catalog-scoped course deletion steps (DSQL-3)."""

from __future__ import annotations

from typing import Protocol

from services.course_deletion.registry import CourseDeletionRegistry

_CATALOG_BATCH_ORDER = 900
_PARENT_ROW_ORDER = 1000
_PARENT_SEP = "\x1f"


class CatalogDeletionRepo(Protocol):
    def delete_lesson_files_for_course(self, course_id: str) -> int: ...

    def delete_lessons_for_course(self, course_id: str) -> int: ...

    def delete_course_modules_for_course(self, course_id: str) -> int: ...

    def delete_course_row(self, course_id: str) -> int: ...

    def delete_lesson_files_for_module(self, course_id: str, module_id: str) -> int: ...

    def delete_lessons_for_module(self, course_id: str, module_id: str) -> int: ...

    def delete_course_module_row(self, course_id: str, module_id: str) -> int: ...

    def delete_lesson_files_for_lesson(self, course_id: str, lesson_id: str) -> int: ...

    def delete_lesson_row(self, course_id: str, lesson_id: str) -> int: ...


def module_deletion_parent_id(course_id: str, module_id: str) -> str:
    return f"{course_id.strip()}{_PARENT_SEP}{module_id.strip()}"


def lesson_deletion_parent_id(course_id: str, lesson_id: str) -> str:
    return f"{course_id.strip()}{_PARENT_SEP}{lesson_id.strip()}"


def split_deletion_parent_id(parent_id: str) -> tuple[str, str]:
    if _PARENT_SEP not in parent_id:
        raise ValueError("invalid composite parent_id")
    course_id, child_id = parent_id.split(_PARENT_SEP, 1)
    cid = course_id.strip()
    child = child_id.strip()
    if not cid or not child:
        raise ValueError("invalid composite parent_id")
    return cid, child


def _split_parent(parent_id: str) -> tuple[str, str]:
    return split_deletion_parent_id(parent_id)


def register_catalog_steps(registry: CourseDeletionRegistry, repo: CatalogDeletionRepo) -> None:
    registry.register(
        name="lesson_files_course",
        order=_CATALOG_BATCH_ORDER,
        scope="course",
        run=lambda course_id: repo.delete_lesson_files_for_course(course_id),
    )
    registry.register(
        name="lessons_course",
        order=_CATALOG_BATCH_ORDER,
        scope="course",
        run=lambda course_id: repo.delete_lessons_for_course(course_id),
    )
    registry.register(
        name="course_modules_course",
        order=_CATALOG_BATCH_ORDER,
        scope="course",
        run=lambda course_id: repo.delete_course_modules_for_course(course_id),
    )
    registry.register(
        name="course_row",
        order=_PARENT_ROW_ORDER,
        scope="course",
        run=lambda course_id: repo.delete_course_row(course_id),
    )

    registry.register(
        name="lesson_files_module",
        order=_CATALOG_BATCH_ORDER,
        scope="module",
        run=lambda parent_id: repo.delete_lesson_files_for_module(*_split_parent(parent_id)),
    )
    registry.register(
        name="lessons_module",
        order=_CATALOG_BATCH_ORDER,
        scope="module",
        run=lambda parent_id: repo.delete_lessons_for_module(*_split_parent(parent_id)),
    )
    registry.register(
        name="course_module_row",
        order=_PARENT_ROW_ORDER,
        scope="module",
        run=lambda parent_id: repo.delete_course_module_row(*_split_parent(parent_id)),
    )

    registry.register(
        name="lesson_files_lesson",
        order=_CATALOG_BATCH_ORDER,
        scope="lesson",
        run=lambda parent_id: repo.delete_lesson_files_for_lesson(*_split_parent(parent_id)),
    )
    registry.register(
        name="lesson_row",
        order=_PARENT_ROW_ORDER,
        scope="lesson",
        run=lambda parent_id: repo.delete_lesson_row(*_split_parent(parent_id)),
    )
