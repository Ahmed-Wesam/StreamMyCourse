"""Unit tests for ``cognito_user_profile_sync/repo.py`` (RDS upsert helpers)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import importlib.util
import pytest

_COGNITO_SRC = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "infrastructure", "lambda", "cognito_user_profile_sync"
    )
)
if _COGNITO_SRC not in sys.path:
    sys.path.insert(0, _COGNITO_SRC)

_DB_TX = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..",
        "infrastructure", "lambda", "catalog", "services", "common", "db_tx.py",
    )
)


@pytest.fixture(autouse=True)
def _register_db_tx() -> None:
    if "db_tx" not in sys.modules:
        spec = importlib.util.spec_from_file_location("db_tx", _DB_TX)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["db_tx"] = mod


import repo as cognito_repo  # noqa: E402


@pytest.fixture(autouse=True)
def reset_cached_factory() -> Any:
    cognito_repo._cached_factory = None
    yield
    cognito_repo._cached_factory = None


def test_build_connection_factory_requires_dsql_endpoint() -> None:
    with pytest.raises(RuntimeError, match="DSQL_ENDPOINT"):
        cognito_repo.build_connection_factory(dsql_endpoint="")


def test_build_connection_factory_rejects_rds_env_with_dsql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DB_HOST", "rds.example")
    with pytest.raises(RuntimeError, match="DSQL_ENDPOINT only"):
        cognito_repo.build_connection_factory(dsql_endpoint="cluster.dsql.example")


def test_factory_delegates_to_dsql_connect() -> None:
    inner = MagicMock(return_value=MagicMock(name="conn"))
    build_dsql = MagicMock(return_value=inner)
    with patch.dict(
        sys.modules,
        {
            "dsql_connect": MagicMock(build_connection_factory=build_dsql),
        },
    ):
        factory = cognito_repo.build_connection_factory(dsql_endpoint="cluster.dsql.example")
        conn = factory()
    build_dsql.assert_called_once_with("cluster.dsql.example")
    inner.assert_called_once()
    assert conn is inner.return_value


def test_set_student_active_session_id_records_last_login_at() -> None:
    """A new student session claim stamps last_login_at."""
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value = cur

    cognito_repo.set_student_active_session_id(lambda: conn, user_sub="user-1", session_id="sess-1")

    sql = cur.execute.call_args.args[0]
    assert "last_login_at" in sql.lower()
    assert "now()" in sql.lower()
    conn.commit.assert_called_once()


def test_upsert_commits_closes_and_warns_when_no_returning_row(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("WARNING")
    cur = MagicMock()
    cur.fetchone.return_value = None
    conn = MagicMock()
    conn.cursor.return_value = cur

    def factory() -> MagicMock:
        return conn

    with caplog.at_level("WARNING"):
        cognito_repo.upsert_user_profile(
            factory, user_sub="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", email="a@b.com", role="student"
        )

    conn.commit.assert_called_once()
    assert "users upsert returned no row" in caplog.text
    assert cur.execute.called


def test_upsert_rollback_and_reraise_on_execute_error() -> None:
    cur = MagicMock()
    cur.execute.side_effect = RuntimeError("db")
    conn = MagicMock()
    conn.cursor.return_value = cur

    def factory() -> MagicMock:
        return conn

    with pytest.raises(RuntimeError, match="db"):
        cognito_repo.upsert_user_profile(factory, user_sub="u1", email="a@b.com", role="student")

    conn.rollback.assert_called_once()


def test_upsert_raises_when_psycopg2_missing(monkeypatch) -> None:
    conn = MagicMock()

    monkeypatch.setattr(cognito_repo, "psycopg2", None)
    with pytest.raises(RuntimeError, match="psycopg2 is not available"):
        cognito_repo.upsert_user_profile(lambda: conn, user_sub="u1", email="e", role="student")


def test_get_cached_connection_factory_builds_once() -> None:
    calls: list[str] = []

    def build(**kwargs: Any) -> Any:
        calls.append("build")
        return lambda: MagicMock(name="conn")

    cfg = MagicMock()
    cfg.dsql_endpoint = "cluster.dsql.example"

    with patch.object(cognito_repo, "build_connection_factory", side_effect=build):
        f1 = cognito_repo.get_cached_connection_factory(cfg)
        f2 = cognito_repo.get_cached_connection_factory(cfg)

    assert f1 is f2
    assert calls == ["build"]
