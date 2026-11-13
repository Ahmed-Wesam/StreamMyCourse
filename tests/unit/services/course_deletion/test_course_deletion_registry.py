"""DSQL-3 S1: CourseDeletionRegistry semantics."""

from __future__ import annotations

import pytest

from services.course_deletion.registry import CourseDeletionRegistry
from services.course_deletion.runner import CourseDeletionRunner


class TestCourseDeletionRegistry:
    def test_steps_run_ascending_order_for_scope(self) -> None:
        registry = CourseDeletionRegistry()
        order_log: list[str] = []
        registry.register(name="second", order=200, scope="course", run=lambda _: order_log.append("second"))
        registry.register(name="first", order=100, scope="course", run=lambda _: order_log.append("first"))
        registry.register(
            name="lesson-only",
            order=50,
            scope="lesson",
            run=lambda _: order_log.append("lesson-only"),
        )
        runner = CourseDeletionRunner(registry)
        runner.run("course", "course-1")
        assert order_log == ["first", "second"]

    def test_unknown_scope_rejected_at_register_time(self) -> None:
        registry = CourseDeletionRegistry()
        with pytest.raises(ValueError, match="scope"):
            registry.register(name="bad", order=1, scope="chapter", run=lambda _: None)  # type: ignore[arg-type]

    def test_23503_exception_propagates_raw(self) -> None:
        registry = CourseDeletionRegistry()

        def fail_fk(parent_id: str) -> None:
            err = Exception("fk violation")
            err.pgcode = "23503"  # type: ignore[attr-defined]
            raise err

        registry.register(name="child_rows", order=100, scope="course", run=fail_fk)
        runner = CourseDeletionRunner(registry)
        with pytest.raises(Exception) as exc_info:
            runner.run("course", "course-1")
        assert getattr(exc_info.value, "pgcode", None) == "23503"

    def test_second_run_of_idempotent_step_succeeds(self) -> None:
        registry = CourseDeletionRegistry()
        calls: list[str] = []

        def zero_row_step(parent_id: str) -> None:
            calls.append(parent_id)

        registry.register(name="attachments", order=100, scope="module", run=zero_row_step)
        runner = CourseDeletionRunner(registry)
        runner.run("module", "mod-1")
        runner.run("module", "mod-1")
        assert calls == ["mod-1", "mod-1"]
