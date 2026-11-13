"""DSQL-6 S5: quiz deletion order 300 and batched SQL."""

from __future__ import annotations

from typing import Any, Callable, Sequence
from unittest.mock import MagicMock

import pytest

from services.course_deletion.catalog import (
    module_deletion_parent_id,
    register_catalog_steps,
    split_deletion_parent_id,
)
from services.course_deletion.registry import CourseDeletionRegistry
from services.course_deletion.runner import CourseDeletionRunner
from services.question_banks.deletion import (
    delete_quiz_course_content,
    register_question_bank_deletion_steps,
)
from services.question_banks.rds_repo import (
    QuestionBankRdsRepository,
    _DELETE_BINDINGS_FOR_COURSE_SQL,
    _DELETE_BINDINGS_FOR_MODULE_SQL,
    _DELETE_BINDINGS_FOR_USER_SQL,
    _DELETE_BINDING_QUESTIONS_FOR_COURSE_SQL,
    _DELETE_MODULE_QUIZZES_FOR_COURSE_SQL,
    _DELETE_QUESTION_BANKS_FOR_COURSE_SQL,
    _DELETE_QUESTIONS_FOR_COURSE_SQL,
    _DELETE_QUIZ_ATTEMPTS_FOR_COURSE_SQL,
    _DELETE_QUIZ_SUBMISSIONS_FOR_COURSE_SQL,
    _DELETE_QUIZ_SUBMISSIONS_FOR_USER_SQL,
)
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


def _quiz_repo(conn: _FakeConn) -> QuestionBankRdsRepository:
    repo = QuestionBankRdsRepository(lambda: conn)
    repo._conn = conn
    return repo


class _FakeDeleter:
    def delete_user_row(self, user_sub: str) -> int:
        return 1


class TestCourseDeletionQuizOrder:
    def test_quiz_step_at_300_runs_before_catalog_900(self) -> None:
        log: list[str] = []
        catalog = MagicMock()
        catalog.delete_lesson_files_for_course.side_effect = lambda _: log.append("files_900")
        quiz = MagicMock()
        quiz.delete_module_quiz_attempt_submissions_for_course.side_effect = (
            lambda _: log.append("quiz")
        )
        quiz.delete_module_quiz_attempts_for_course.return_value = 0
        quiz.delete_binding_questions_for_course.return_value = 0
        quiz.delete_bindings_for_course.return_value = 0
        quiz.delete_module_quizzes_for_course.return_value = 0
        quiz.delete_questions_for_course.return_value = 0
        quiz.delete_question_banks_for_course.return_value = 0
        registry = CourseDeletionRegistry()
        register_question_bank_deletion_steps(registry, quiz)
        register_catalog_steps(registry, catalog)
        CourseDeletionRunner(registry).run("course", _CID)
        assert log[0] == "quiz"
        assert "files_900" in log
        assert log.index("quiz") < log.index("files_900")

    def test_course_step_leaf_order_inside_one_callback(self) -> None:
        calls: list[str] = []
        quiz = MagicMock()

        def track(name: str) -> Callable[..., int]:
            return lambda *args, **kwargs: calls.append(name) or 0

        quiz.delete_module_quiz_attempt_submissions_for_course.side_effect = track(
            "submissions"
        )
        quiz.delete_module_quiz_attempts_for_course.side_effect = track("attempts")
        quiz.delete_binding_questions_for_course.side_effect = track("binding_questions")
        quiz.delete_bindings_for_course.side_effect = track("bindings")
        quiz.delete_module_quizzes_for_course.side_effect = track("module_quizzes")
        quiz.delete_questions_for_course.side_effect = track("questions")
        quiz.delete_question_banks_for_course.side_effect = track("question_banks")
        delete_quiz_course_content(quiz, _CID)
        assert calls == [
            "submissions",
            "attempts",
            "binding_questions",
            "bindings",
            "module_quizzes",
            "questions",
            "question_banks",
        ]

    def test_module_scope_does_not_delete_banks_or_questions(self) -> None:
        quiz = MagicMock()
        registry = CourseDeletionRegistry()
        register_question_bank_deletion_steps(registry, quiz)
        parent = module_deletion_parent_id(_CID, _MID)
        CourseDeletionRunner(registry).run("module", parent)
        cid, mid = split_deletion_parent_id(parent)
        quiz.delete_module_quiz_attempt_submissions_for_module.assert_called_with(cid, mid)
        quiz.delete_question_banks_for_course.assert_not_called()
        quiz.delete_questions_for_course.assert_not_called()
        quiz.delete_module_quizzes_for_course.assert_not_called()

    def test_lesson_scope_has_no_quiz_step(self) -> None:
        registry = CourseDeletionRegistry()
        register_question_bank_deletion_steps(registry, MagicMock())
        assert registry.ordered_steps("lesson") == []


class TestUserDeletionQuizOrder:
    def test_quiz_student_rows_at_order_300(self) -> None:
        registry = UserDeletionRegistry()
        register_operator_user_steps(
            registry,
            _FakeDeleter(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        steps = registry.ordered_steps()
        quiz_steps = [s for s in steps if s.name == "quiz_student_rows"]
        assert len(quiz_steps) == 1
        assert quiz_steps[0].order == 300
        orders = sorted({s.order for s in steps})
        assert orders.index(200) < orders.index(300) < orders.index(1000)

    def test_quiz_runs_after_purchases_before_users_row(self) -> None:
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
            lambda _: log.append("quiz")
        )
        quiz.delete_module_quiz_attempts_for_user.return_value = 0
        quiz.delete_binding_questions_for_user.return_value = 0
        quiz.delete_bindings_for_user.return_value = 0
        registry = UserDeletionRegistry()
        register_operator_user_steps(
            registry, _FakeDeleter(), progress, notes, purchases, quiz
        )
        UserDeletionService(registry).delete_user(_SUB)
        assert log.index("purchases") < log.index("quiz")
        quiz.delete_module_quiz_attempt_submissions_for_user.assert_called_once_with(_SUB)


class TestBatchedDeleteSql:
    @pytest.mark.parametrize(
        "sql",
        [
            _DELETE_QUIZ_SUBMISSIONS_FOR_USER_SQL,
            _DELETE_QUIZ_ATTEMPTS_FOR_COURSE_SQL,
            _DELETE_BINDING_QUESTIONS_FOR_COURSE_SQL,
            _DELETE_BINDINGS_FOR_USER_SQL,
            _DELETE_BINDINGS_FOR_MODULE_SQL,
            _DELETE_MODULE_QUIZZES_FOR_COURSE_SQL,
            _DELETE_QUESTIONS_FOR_COURSE_SQL,
            _DELETE_QUESTION_BANKS_FOR_COURSE_SQL,
        ],
    )
    def test_sql_uses_limit_1000_and_using(self, sql: str) -> None:
        lowered = sql.lower()
        assert "limit 1000" in lowered
        assert "using" in lowered
        assert "question_banks" not in lowered or "delete from question_banks" in lowered

    def test_module_sql_does_not_mention_question_banks_table(self) -> None:
        lowered = _DELETE_BINDINGS_FOR_MODULE_SQL.lower()
        assert "question_banks" not in lowered

    def test_user_delete_second_batch_deletes_zero_rows(self) -> None:
        conn = _FakeConn()
        calls = {"n": 0}

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.rowcount = 2 if calls["n"] == 0 else 0
            calls["n"] += 1

        conn.cursor_obj._execute_hook = hook
        total = _quiz_repo(conn).delete_bindings_for_user(_SUB)
        assert total == 2
        assert len(conn.cursor_obj.executions) == 2
        assert conn.cursor_obj.executions[0][1] == (_SUB,)
        assert conn.cursor_obj.executions[1][1] == (_SUB,)

    def test_course_bindings_delete_invokes_batched_sql(self) -> None:
        conn = _FakeConn()
        conn.cursor_obj.rowcount = 0
        _quiz_repo(conn).delete_bindings_for_course(_CID)
        sql = conn.cursor_obj.executions[0][0]
        assert "student_module_quiz_bindings" in sql.lower()
        assert _DELETE_BINDINGS_FOR_COURSE_SQL.strip() in sql or "using" in sql.lower()
