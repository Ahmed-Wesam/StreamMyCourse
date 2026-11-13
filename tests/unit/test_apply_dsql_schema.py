"""Unit tests for scripts/apply-dsql-schema.py (fake connection boundary)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_APPLIER = _ROOT / "scripts" / "apply-dsql-schema.py"


@pytest.fixture(scope="module")
def applier():
    assert _APPLIER.is_file(), f"missing {_APPLIER}"
    spec = importlib.util.spec_from_file_location("apply_dsql_schema", _APPLIER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeCursor:
    def __init__(self, fetch_rows: list[tuple[Any, ...]] | None = None) -> None:
        self.executed: list[tuple[str, tuple[Any, ...] | None]] = []
        self._fetch_rows = list(fetch_rows or [])
        self.description = [("job_id",)] if fetch_rows is not None else None

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...] | None = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> tuple[Any, ...] | None:
        if self._fetch_rows:
            return self._fetch_rows.pop(0)
        return None


class FakeConn:
    def __init__(self) -> None:
        self.autocommit = False
        self.commits = 0
        self.rollbacks = 0
        self._cursors: list[FakeCursor] = []

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def cursor(self) -> FakeCursor:
        cur = FakeCursor()
        self._cursors.append(cur)
        return cur


def test_split_semicolon_inside_string_literal(applier) -> None:
    sql = "INSERT INTO app.t (c) VALUES ('a;b');\nSELECT 1;"
    parts = applier.split_sql_statements(sql)
    assert len(parts) == 2
    assert "a;b" in parts[0]
    assert parts[1].strip().startswith("SELECT 1")


def test_one_statement_per_commit(applier) -> None:
    conn = FakeConn()
    statements = [
        "CREATE SCHEMA app;",
        "CREATE TABLE app.foo (id INT);",
    ]
    applier.apply_statements(conn, statements)
    assert conn.commits == len(statements)
    assert len(conn._cursors[0].executed) >= 1


def test_async_index_waits_for_job(applier) -> None:
    conn = FakeConn()
    cur = FakeCursor(fetch_rows=[("job-abc",)])
    conn.cursor = lambda: cur  # type: ignore[method-assign]
    applier.execute_one_statement(
        conn,
        "CREATE UNIQUE INDEX ASYNC idx_x ON app.foo (id);",
    )
    assert conn.commits == 2
    wait_calls = [e for e in cur.executed if e[0].startswith("CALL sys.wait_for_job")]
    assert len(wait_calls) == 1
    assert wait_calls[0][1] == ("job-abc",)


def test_async_job_wait_failure_raises(applier) -> None:
    conn = FakeConn()
    cur = FakeCursor(fetch_rows=[("job-fail",)])

    def execute(sql: str, params: tuple[Any, ...] | None = None) -> None:
        cur.executed.append((sql, params))
        if sql.startswith("CALL sys.wait_for_job"):
            raise RuntimeError("job failed")

    cur.execute = execute  # type: ignore[method-assign]
    conn.cursor = lambda: cur  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="job failed"):
        applier.execute_one_statement(
            conn,
            "CREATE INDEX ASYNC idx_y ON app.foo (id);",
        )


def test_skip_schema_when_version_recorded(applier) -> None:
    conn = FakeConn()

    def cursor_factory():
        if not conn._cursors:
            c = FakeCursor()
            c.fetchone = lambda: (1,)  # version exists
            c.description = [("exists",)]
            conn._cursors.append(c)
            return c
        return FakeCursor()

    conn.cursor = cursor_factory  # type: ignore[method-assign]
    applied = applier.apply_migration_file(
        conn,
        sql_text="CREATE TABLE app.x (id INT);",
        version="0001",
    )
    assert applied is False
    assert conn.commits == 1


def test_skip_iam_grant_when_mapping_exists(applier) -> None:
    conn = FakeConn()
    arn = "arn:aws:iam::123456789012:role/StreamMyCourse-CatalogLambdaRole-prod"

    calls: list[FakeCursor] = []

    def cursor_factory():
        c = FakeCursor()
        c.description = [("iam_role",)]
        c.fetchone = lambda: (arn,)
        calls.append(c)
        return c

    conn.cursor = cursor_factory  # type: ignore[method-assign]
    applier.apply_iam_grant(conn, arn)
    assert conn.commits == 1
    assert not any(
        e[0].startswith("AWS IAM GRANT") for e in calls[0].executed
    )


def test_iam_grant_executed_when_absent(applier) -> None:
    conn = FakeConn()
    arn = "arn:aws:iam::123456789012:role/StreamMyCourse-CatalogLambdaRole-prod"
    cur = FakeCursor()
    cur.description = [("iam_role",)]
    cur.fetchone = lambda: None
    conn.cursor = lambda: cur  # type: ignore[method-assign]
    applier.apply_iam_grant(conn, arn)
    grants = [e for e in cur.executed if e[0].startswith("AWS IAM GRANT")]
    assert len(grants) == 1
    assert arn in grants[0][0]


def test_connection_error_host_only(applier) -> None:
    err = applier.connection_error("cluster.dsql.eu-west-1.on.aws", ValueError("secret token"))
    assert str(err) == "DSQL connection failed for host cluster.dsql.eu-west-1.on.aws"
    assert "token" not in str(err)
    assert "secret" not in str(err).lower()

