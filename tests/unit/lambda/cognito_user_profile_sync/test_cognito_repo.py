"""Unit tests for ``cognito_user_profile_sync/repo.py`` (RDS upsert helpers)."""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

_COGNITO_SRC = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "infrastructure", "lambda", "cognito_user_profile_sync"
    )
)
if _COGNITO_SRC not in sys.path:
    sys.path.insert(0, _COGNITO_SRC)

import repo as cognito_repo  # noqa: E402


@pytest.fixture(autouse=True)
def reset_cached_factory() -> Any:
    cognito_repo._cached_factory = None
    yield
    cognito_repo._cached_factory = None


def test_build_connection_factory_requires_secret_arn() -> None:
    with pytest.raises(RuntimeError, match="DB_SECRET_ARN"):
        cognito_repo.build_connection_factory(
            db_secret_arn="", db_host="h", db_name="n", db_port=5432
        )


def test_build_connection_factory_requires_db_host() -> None:
    with pytest.raises(RuntimeError, match="DB_HOST"):
        cognito_repo.build_connection_factory(
            db_secret_arn="arn:x", db_host="", db_name="n", db_port=5432
        )


def test_factory_fetches_secret_and_connects_with_expected_kwargs() -> None:
    sm = MagicMock()
    sm.get_secret_value.return_value = {
        "SecretString": json.dumps({"username": "u", "password": "p"}),
    }
    conn = MagicMock()
    connect_calls: list[dict[str, Any]] = []

    def fake_connect(**kwargs: Any) -> MagicMock:
        connect_calls.append(kwargs)
        return conn

    factory = cognito_repo.build_connection_factory(
        db_secret_arn="arn:aws:secretsmanager:us-east-1:1:secret:x",
        db_host="db.example",
        db_name="appdb",
        db_port=5432,
    )
    with (
        patch.object(cognito_repo, "_secretsmanager_client", return_value=sm),
        patch.object(cognito_repo, "_psycopg2_connect", side_effect=fake_connect),
    ):
        c = factory()

    assert c is conn
    sm.get_secret_value.assert_called_once_with(
        SecretId="arn:aws:secretsmanager:us-east-1:1:secret:x"
    )
    assert connect_calls == [
        {
            "host": "db.example",
            "port": 5432,
            "dbname": "appdb",
            "user": "u",
            "password": "p",
            "sslmode": "require",
            "connect_timeout": 5,
        }
    ]


def test_factory_invalid_secret_json_raises() -> None:
    sm = MagicMock()
    sm.get_secret_value.return_value = {"SecretString": "not-json"}
    factory = cognito_repo.build_connection_factory(
        db_secret_arn="arn:x",
        db_host="h",
        db_name="n",
        db_port=5432,
    )
    with (
        patch.object(cognito_repo, "_secretsmanager_client", return_value=sm),
        patch.object(cognito_repo, "_psycopg2_connect", MagicMock()),
        pytest.raises(RuntimeError, match="not valid JSON"),
    ):
        factory()


def test_factory_missing_user_or_password_raises() -> None:
    sm = MagicMock()
    sm.get_secret_value.return_value = {"SecretString": json.dumps({"username": ""})}
    factory = cognito_repo.build_connection_factory(
        db_secret_arn="arn:x", db_host="h", db_name="n", db_port=5432
    )
    with (
        patch.object(cognito_repo, "_secretsmanager_client", return_value=sm),
        patch.object(cognito_repo, "_psycopg2_connect", MagicMock()),
        pytest.raises(RuntimeError, match="username/password"),
    ):
        factory()


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
    conn.close.assert_called_once()
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
    conn.close.assert_called_once()


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
    cfg.db_secret_arn = "arn:x"
    cfg.db_host = "h"
    cfg.db_name = "n"
    cfg.db_port = 5432

    with patch.object(cognito_repo, "build_connection_factory", side_effect=build):
        f1 = cognito_repo.get_cached_connection_factory(cfg)
        f2 = cognito_repo.get_cached_connection_factory(cfg)

    assert f1 is f2
    assert calls == ["build"]
