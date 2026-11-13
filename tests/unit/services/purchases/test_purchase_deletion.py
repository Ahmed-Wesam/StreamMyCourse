"""DSQL-5 S4: batched purchase delete on operator user deletion."""

from __future__ import annotations

from typing import Any, Callable, Sequence
from unittest.mock import MagicMock

from services.purchases.repo import (
    PurchaseRdsRepository,
    _DELETE_PURCHASES_FOR_USER_SQL,
)
from services.user_deletion.operator import register_operator_user_steps
from services.user_deletion.registry import UserDeletionRegistry
from services.user_deletion.service import UserDeletionService

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


def _purchase_repo(conn: _FakeConn) -> PurchaseRdsRepository:
    repo = PurchaseRdsRepository(lambda: conn, deployment_environment="prod")
    repo._conn = conn
    return repo


class _FakeDeleter:
    def delete_user_row(self, user_sub: str) -> int:
        return 1


class TestPurchaseDeletionSql:
    def test_sql_uses_limit_1000_and_user_sub(self) -> None:
        lowered = _DELETE_PURCHASES_FOR_USER_SQL.lower()
        assert "limit 1000" in lowered
        assert "user_sub = %s" in lowered
        assert "payment_webhook_events" not in lowered

    def test_second_batch_deletes_zero_rows(self) -> None:
        conn = _FakeConn()
        calls = {"n": 0}

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.rowcount = 3 if calls["n"] == 0 else 0
            calls["n"] += 1

        conn.cursor_obj._execute_hook = hook
        repo = _purchase_repo(conn)
        total = repo.delete_purchases_for_user(_SUB)
        assert total == 3
        assert len(conn.cursor_obj.executions) == 2
        assert conn.cursor_obj.executions[0][1] == (_SUB,)
        assert conn.cursor_obj.executions[1][1] == (_SUB,)


class TestPurchaseDeletionRegistration:
    def test_purchases_step_at_order_200(self) -> None:
        registry = UserDeletionRegistry()
        progress = MagicMock()
        notes = MagicMock()
        purchases = MagicMock()
        quiz = MagicMock()
        register_operator_user_steps(
            registry,
            _FakeDeleter(),
            progress,
            notes,
            purchases,
            quiz,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        steps = registry.ordered_steps()
        purchase_steps = [s for s in steps if s.name == "purchases"]
        assert len(purchase_steps) == 1
        assert purchase_steps[0].order == 200

    def test_purchases_runs_after_learning_before_users(self) -> None:
        log: list[str] = []
        progress = MagicMock()
        progress.delete_lesson_progress_for_user.side_effect = lambda _: log.append("progress")
        progress.delete_learning_activity_days_for_user.side_effect = lambda _: log.append("days")
        notes = MagicMock()
        notes.delete_lesson_notes_for_user.side_effect = lambda _: log.append("notes")
        purchases = MagicMock()
        purchases.delete_purchases_for_user.side_effect = lambda _: log.append("purchases")
        quiz = MagicMock()
        registry = UserDeletionRegistry()
        register_operator_user_steps(
            registry,
            _FakeDeleter(),
            progress,
            notes,
            purchases,
            quiz,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        UserDeletionService(registry).delete_user(_SUB)
        assert log == [
            "progress",
            "notes",
            "days",
            "purchases",
        ]
