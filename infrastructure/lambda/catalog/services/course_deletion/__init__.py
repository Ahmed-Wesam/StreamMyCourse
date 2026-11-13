"""Course subtree deletion registry (no HTTP, no Cognito)."""

from services.course_deletion.catalog import (
    lesson_deletion_parent_id,
    module_deletion_parent_id,
    register_catalog_steps,
    split_deletion_parent_id,
)
from services.course_deletion.registry import CourseDeletionRegistry, DeletionScope, DeletionStep
from services.course_deletion.runner import CourseDeletionRunner

__all__ = [
    "CourseDeletionRegistry",
    "CourseDeletionRunner",
    "DeletionScope",
    "DeletionStep",
    "lesson_deletion_parent_id",
    "module_deletion_parent_id",
    "register_catalog_steps",
    "split_deletion_parent_id",
]
