"""Unit tests for services/common/db_tx.py."""

from __future__ import annotations

from typing import Any, Callable, List, Sequence
from unittest.mock import MagicMock

import pytest

from services.common import db_tx


class _PgError(Exception):
    def __init__(self, pgcode: str | None = None) -> None:
        super().__init__(pgcode or "err")
        self.pgcode = pgcode


@pytest.fixture
def fake_conn() -> MagicMock:
    conn = MagicMock(name="conn")
    conn.autocommit = True
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    cur = MagicMock()
    cur.rowcount = 0
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn


def test_run_transaction_success_commits_once(fake_conn: MagicMock) -> None:
    calls: List[str] = []

    def body() -> None:
        calls.append("body")

    db_tx.run_transaction(fake_conn, body, sleep=lambda _s: None)

    assert calls == ["body"]
    fake_conn.commit.assert_called_once()
    fake_conn.rollback.assert_not_called()
    assert fake_conn.autocommit is True


def test_run_transaction_retries_40001_then_commits_once(fake_conn: MagicMock) -> None:
    attempts = {"n": 0}

    def body() -> None:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _PgError("40001")

    db_tx.run_transaction(fake_conn, body, sleep=lambda _s: None)

    assert attempts["n"] == 2
    fake_conn.commit.assert_called_once()
    assert fake_conn.rollback.call_count == 1


def test_run_transaction_three_40001_raises_last(fake_conn: MagicMock) -> None:
    def body() -> None:
        raise _PgError("40001")

    with pytest.raises(_PgError) as exc_info:
        db_tx.run_transaction(fake_conn, body, attempts=3, sleep=lambda _s: None)

    assert exc_info.value.pgcode == "40001"
    assert fake_conn.rollback.call_count == 3
    fake_conn.commit.assert_not_called()


def test_run_transaction_does_not_retry_23503(fake_conn: MagicMock) -> None:
    def body() -> None:
        raise _PgError("23503")

    with pytest.raises(_PgError) as exc_info:
        db_tx.run_transaction(fake_conn, body, sleep=lambda _s: None)

    assert exc_info.value.pgcode == "23503"
    fake_conn.rollback.assert_called_once()
    fake_conn.commit.assert_not_called()


def test_delete_in_batches_stops_at_zero_rowcount(fake_conn: MagicMock) -> None:
    cur = fake_conn.cursor.return_value.__enter__.return_value
    rowcounts = iter([500, 0])
    cur.rowcount = property(lambda self: next(rowcounts))  # type: ignore[method-assign]

    def rowcount_set() -> int:
        return next(rowcounts)

    cur.rowcount = 500
    calls = {"n": 0}

    def execute(sql: str, params: Sequence[Any]) -> None:
        calls["n"] += 1
        cur.rowcount = 500 if calls["n"] == 1 else 0

    cur.execute = execute

    total = db_tx.delete_in_batches(
        fake_conn,
        "DELETE FROM app.scratch WHERE id IN (SELECT id FROM app.scratch WHERE parent_id = %s LIMIT 1000)",
        ("parent",),
        sleep=lambda _s: None,
    )

    assert total == 500
    assert calls["n"] == 2


def test_delete_in_batches_never_exceeds_batch_limit(fake_conn: MagicMock) -> None:
    cur = fake_conn.cursor.return_value.__enter__.return_value
    calls = {"n": 0, "max_rowcount": 0}

    def execute(sql: str, params: Sequence[Any]) -> None:
        calls["n"] += 1
        cur.rowcount = 1000
        calls["max_rowcount"] = max(calls["max_rowcount"], cur.rowcount)
        if calls["n"] >= 3:
            cur.rowcount = 0

    cur.execute = execute

    db_tx.delete_in_batches(
        fake_conn,
        "DELETE FROM app.scratch WHERE id IN (SELECT id FROM app.scratch WHERE parent_id = %s LIMIT 1000)",
        ("parent",),
        sleep=lambda _s: None,
    )

    assert calls["max_rowcount"] <= 1000
