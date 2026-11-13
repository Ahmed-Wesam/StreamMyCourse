"""DSQL-7a S5: assignment deletion order 400 and batched SQL."""

from __future__ import annotations

from typing import Any, Callable, Sequence
from unittest.mock import MagicMock

import pytest

from services.assignments.deletion import (
    delete_assignment_children_for_course,
    delete_assignment_children_for_module,
    register_assignment_deletion_steps,
)
from services.assignments.rds_repo import (
    AssignmentsRdsRepository,
    _DELETE_ASSIGNMENT_SUBMISSIONS_FOR_USER_SQL,
)
from services.course_deletion.catalog import (
    module_deletion_parent_id,
    register_catalog_steps,
    split_deletion_parent_id,
)
from services.course_deletion.registry import CourseDeletionRegistry
from services.course_deletion.runner import CourseDeletionRunner
from services.user_deletion.operator import register_operator_user_steps
from services.user_deletion.registry import UserDeletionRegistry
from services.user_deletion.service import UserDeletionService

_CID = "11111111-1111-4111-8111-111111111111"
_MID = "22222222-2222-4222-8222-222222222222"
_SUB = "user-sub-1"


class _FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[Any, ...]]] = []
        self.rowcount = 0
        self._execute_hook: Callable[[str, Sequence[Any]], None] | None = None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))
        if self._execute_hook:
            self._execute_hook(sql, params)
        else:
            self.rowcount = 0

    def __enter__(self) -> "_FakeCursor":
        return self

    def __exit__(self, *args: object) -> None:
        pass


class _FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = _FakeCursor()
        self.autocommit = True

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _repo(conn: _FakeConn) -> AssignmentsRdsRepository:
    repo = AssignmentsRdsRepository(lambda: conn)
    repo._conn = conn
    return repo


class _FakeDeleter:
    def delete_user_row(self, user_sub: str) -> int:
        return 1


class TestCourseDeletionAssignmentOrder:
    def test_assignment_step_at_400_runs_before_catalog_900(self) -> None:
        log: list[str] = []
        catalog = MagicMock()
        catalog.delete_lesson_files_for_course.side_effect = lambda _: log.append("files_900")
        assignments = MagicMock()
        assignments.delete_assignment_grade_scores_for_course.side_effect = (
            lambda _: log.append("scores")
        )
        assignments.delete_assignment_grades_for_course.return_value = 0
        assignments.delete_assignment_submission_files_for_course.return_value = 0
        assignments.delete_assignment_submissions_for_course.return_value = 0
        registry = CourseDeletionRegistry()
        register_assignment_deletion_steps(registry, assignments)
        register_catalog_steps(registry, catalog)
        CourseDeletionRunner(registry).run("course", _CID)
        assert log.index("scores") < log.index("files_900")

    def test_course_step_leaf_order_inside_one_callback(self) -> None:
        calls: list[str] = []
        assignments = MagicMock()

        def track(name: str) -> Callable[..., int]:
            return lambda *args, **kwargs: calls.append(name) or 0

        assignments.delete_assignment_grade_scores_for_course.side_effect = track(
            "scores"
        )
        assignments.delete_assignment_grades_for_course.side_effect = track("grades")
        assignments.delete_assignment_submission_files_for_course.side_effect = track(
            "files"
        )
        assignments.delete_assignment_submissions_for_course.side_effect = track(
            "submissions"
        )
        delete_assignment_children_for_course(assignments, _CID)
        assert calls == ["scores", "grades", "files", "submissions"]

    def test_module_scope_does_not_delete_assignment_row(self) -> None:
        assignments = MagicMock()
        registry = CourseDeletionRegistry()
        register_assignment_deletion_steps(registry, assignments)
        parent = module_deletion_parent_id(_CID, _MID)
        CourseDeletionRunner(registry).run("module", parent)
        cid, mid = split_deletion_parent_id(parent)
        assignments.delete_assignment_submissions_for_module.assert_called_with(cid, mid)
        assignments.delete_assignment_grade_scores_for_course.assert_not_called()


class TestUserDeletionAssignmentOrder:
    def test_assignment_children_at_order_400(self) -> None:
        registry = UserDeletionRegistry()
        register_operator_user_steps(
            registry,
            _FakeDeleter(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        steps = registry.ordered_steps()
        names = [s.name for s in steps if s.order == 400]
        assert "assignment_certificate_research_rows" in names
        orders = sorted({s.order for s in steps})
        assert orders.index(300) < orders.index(400) < orders.index(1000)

    def test_assignment_deletes_after_quiz_before_identity(self) -> None:
        log: list[str] = []
        quiz = MagicMock()
        quiz.delete_module_quiz_attempt_submissions_for_user.side_effect = (
            lambda _: log.append("quiz")
        )
        quiz.delete_module_quiz_attempts_for_user.return_value = 0
        quiz.delete_binding_questions_for_user.return_value = 0
        quiz.delete_bindings_for_user.return_value = 0
        assignments = MagicMock()
        assignments.delete_assignment_grade_scores_for_user.side_effect = (
            lambda _: log.append("assignments")
        )
        assignments.delete_assignment_grades_for_user.return_value = 0
        assignments.delete_assignment_submission_files_for_user.return_value = 0
        assignments.delete_assignment_submissions_for_user.return_value = 0
        registry = UserDeletionRegistry()
        register_operator_user_steps(
            registry,
            _FakeDeleter(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            quiz,
            assignments,
        )
        UserDeletionService(registry).delete_user(_SUB)
        assert log.index("quiz") < log.index("assignments")


class TestBatchedDeleteSql:
    @pytest.mark.parametrize(
        "sql",
        [_DELETE_ASSIGNMENT_SUBMISSIONS_FOR_USER_SQL],
    )
    def test_sql_uses_limit_1000_and_using(self, sql: str) -> None:
        lowered = sql.lower()
        assert "limit 1000" in lowered
        assert "using" in lowered

    def test_user_delete_second_batch_deletes_zero_rows(self) -> None:
        conn = _FakeConn()
        calls = {"n": 0}

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.rowcount = 2 if calls["n"] == 0 else 0
            calls["n"] += 1

        conn.cursor_obj._execute_hook = hook
        total = _repo(conn).delete_assignment_submissions_for_user(_SUB)
        assert total == 2
        assert len(conn.cursor_obj.executions) == 2
