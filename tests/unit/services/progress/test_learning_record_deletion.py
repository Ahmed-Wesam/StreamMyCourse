"""DSQL-4 S4: learning-record deletion registration and batched SQL."""

from __future__ import annotations

from typing import Any, Callable, Sequence
from unittest.mock import MagicMock

import pytest

from services.course_deletion.catalog import (
    module_deletion_parent_id,
    split_deletion_parent_id,
)
from services.course_deletion.registry import CourseDeletionRegistry
from services.course_deletion.runner import CourseDeletionRunner
from services.lesson_notes.deletion import register_lesson_note_deletion_steps
from services.lesson_notes.rds_repo import (
    LessonNotesRdsRepository,
    _DELETE_LESSON_NOTES_FOR_COURSE_SQL,
    _DELETE_LESSON_NOTES_FOR_LESSON_SQL,
    _DELETE_LESSON_NOTES_FOR_MODULE_SQL,
    _DELETE_LESSON_NOTES_FOR_USER_SQL,
)
from services.progress.deletion import register_progress_deletion_steps
from services.progress.rds_repo import (
    LessonProgressRdsRepository,
    _DELETE_LEARNING_ACTIVITY_DAYS_FOR_USER_SQL,
    _DELETE_LESSON_PROGRESS_FOR_COURSE_SQL,
    _DELETE_LESSON_PROGRESS_FOR_LESSON_SQL,
    _DELETE_LESSON_PROGRESS_FOR_MODULE_SQL,
    _DELETE_LESSON_PROGRESS_FOR_USER_SQL,
)
from services.user_deletion.identity import register_identity_steps
from services.user_deletion.operator import register_operator_user_steps
from services.user_deletion.registry import UserDeletionRegistry
from services.user_deletion.service import UserDeletionService

_CID = "11111111-1111-4111-8111-111111111111"
_MID = "22222222-2222-4222-8222-222222222222"
_LID = "33333333-3333-4333-8333-333333333333"
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

    def __enter__(self) -> _FakeCursor:
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


def _progress_repo(conn: _FakeConn) -> LessonProgressRdsRepository:
    repo = LessonProgressRdsRepository(lambda: conn)
    repo._conn = conn
    return repo


def _notes_repo(conn: _FakeConn) -> LessonNotesRdsRepository:
    repo = LessonNotesRdsRepository(lambda: conn)
    repo._conn = conn
    return repo


class _FakeDeleter:
    def delete_user_row(self, user_sub: str) -> int:
        return 1


class TestUserDeletionOrder:
    def test_learning_steps_run_before_users_row(self) -> None:
        log: list[str] = []
        progress = MagicMock()
        progress.delete_lesson_progress_for_user.side_effect = lambda _: log.append("progress")
        progress.delete_learning_activity_days_for_user.side_effect = lambda _: log.append("days")
        notes = MagicMock()
        notes.delete_lesson_notes_for_user.side_effect = lambda _: log.append("notes")
        purchases = MagicMock()
        purchases.delete_purchases_for_user.side_effect = lambda _: log.append("purchases")
        quiz = MagicMock()
        quiz.delete_module_quiz_attempt_submissions_for_user.side_effect = (
            lambda _: log.append("quiz_submissions")
        )
        quiz.delete_module_quiz_attempts_for_user.side_effect = lambda _: log.append("quiz_attempts")
        quiz.delete_binding_questions_for_user.side_effect = lambda _: log.append("quiz_bq")
        quiz.delete_bindings_for_user.side_effect = lambda _: log.append("quiz_bindings")
        registry = UserDeletionRegistry()
        register_operator_user_steps(registry, _FakeDeleter(), progress, notes, purchases, quiz)
        UserDeletionService(registry).delete_user(_SUB)
        assert log == [
            "progress",
            "notes",
            "days",
            "purchases",
            "quiz_submissions",
            "quiz_attempts",
            "quiz_bq",
            "quiz_bindings",
        ]
        steps = registry.ordered_steps()
        assert [s.order for s in steps] == [100, 100, 100, 200, 300, 1000]
        assert steps[-1].name == "users"

    def test_users_step_alone_at_1000(self) -> None:
        registry = UserDeletionRegistry()
        register_identity_steps(registry, _FakeDeleter())
        assert registry.ordered_steps()[0].order == 1000


class TestCourseDeletionScopes:
    def test_order_100_steps_for_all_scopes(self) -> None:
        progress = MagicMock()
        notes = MagicMock()
        registry = CourseDeletionRegistry()
        register_progress_deletion_steps(registry, progress)
        register_lesson_note_deletion_steps(registry, notes)
        for scope in ("course", "module", "lesson"):
            steps = registry.ordered_steps(scope)  # type: ignore[arg-type]
            assert steps[0].order == 100
            assert steps[1].order == 100
            assert steps[0].name.startswith("lesson_progress")
            assert steps[1].name.startswith("lesson_notes")

    def test_module_parent_round_trips(self) -> None:
        parent = module_deletion_parent_id(_CID, _MID)
        assert split_deletion_parent_id(parent) == (_CID, _MID)
        registry = CourseDeletionRegistry()
        progress = MagicMock()
        notes = MagicMock()
        register_progress_deletion_steps(registry, progress)
        register_lesson_note_deletion_steps(registry, notes)
        CourseDeletionRunner(registry).run("module", parent)
        progress.delete_lesson_progress_for_module.assert_called_with(_CID, _MID)
        notes.delete_lesson_notes_for_module.assert_called_with(_CID, _MID)


class TestBatchedDeleteSql:
    def test_progress_sql_uses_limit_and_using(self) -> None:
        for sql in (
            _DELETE_LESSON_PROGRESS_FOR_USER_SQL,
            _DELETE_LESSON_PROGRESS_FOR_COURSE_SQL,
            _DELETE_LESSON_PROGRESS_FOR_MODULE_SQL,
            _DELETE_LESSON_PROGRESS_FOR_LESSON_SQL,
            _DELETE_LEARNING_ACTIVITY_DAYS_FOR_USER_SQL,
        ):
            lowered = sql.lower()
            assert "limit 1000" in lowered
            assert "using" in lowered
            assert "enrollments" not in lowered

    def test_notes_sql_uses_limit_1000(self) -> None:
        for sql in (
            _DELETE_LESSON_NOTES_FOR_USER_SQL,
            _DELETE_LESSON_NOTES_FOR_COURSE_SQL,
            _DELETE_LESSON_NOTES_FOR_MODULE_SQL,
            _DELETE_LESSON_NOTES_FOR_LESSON_SQL,
        ):
            lowered = sql.lower()
            assert "limit 1000" in lowered
            assert "enrollments" not in lowered

    def test_progress_course_delete_invokes_batched_sql(self) -> None:
        conn = _FakeConn()
        calls = {"n": 0}

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.rowcount = 1 if calls["n"] == 0 else 0
            calls["n"] += 1

        conn.cursor_obj._execute_hook = hook
        total = _progress_repo(conn).delete_lesson_progress_for_course(_CID)
        assert total == 1
        sql = conn.cursor_obj.executions[0][0]
        assert "lesson_progress" in sql.lower()
        assert "using" in sql.lower()

    def test_notes_lesson_delete_invokes_batched_sql(self) -> None:
        conn = _FakeConn()
        calls = {"n": 0}

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.rowcount = 2 if calls["n"] == 0 else 0
            calls["n"] += 1

        conn.cursor_obj._execute_hook = hook
        total = _notes_repo(conn).delete_lesson_notes_for_lesson(_CID, _LID)
        assert total == 2
        sql = conn.cursor_obj.executions[0][0]
        assert "lesson_notes" in sql.lower()
        assert "limit 1000" in sql.lower()
