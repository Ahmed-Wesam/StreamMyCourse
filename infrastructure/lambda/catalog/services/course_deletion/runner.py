"""Runs registered course-deletion steps for a scope in ascending order."""

from __future__ import annotations

from services.course_deletion.registry import CourseDeletionRegistry, DeletionScope


class CourseDeletionRunner:
    def __init__(self, registry: CourseDeletionRegistry) -> None:
        self._registry = registry

    def run(self, scope: DeletionScope, parent_id: str) -> None:
        pid = (parent_id or "").strip()
        if not pid:
            raise ValueError("parent_id is required")
        for step in self._registry.ordered_steps(scope):
            step.run(pid)
