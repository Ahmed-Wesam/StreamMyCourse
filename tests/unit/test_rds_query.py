"""Unit tests for the invoke-only RDS query / catalog-wipe Lambda."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_INDEX = _ROOT / "infrastructure" / "lambda" / "rds_query" / "index.py"


@pytest.fixture(scope="module")
def rds_query():
    spec = importlib.util.spec_from_file_location("rds_query_index", _INDEX)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_rejects_confirm_mismatch(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:aws:secretsmanager:eu-west-1:123:secret:x")
    out = rds_query.handler({"confirm": "prod", "sql": "SELECT 1"}, None)
    assert out["ok"] is False


def test_rejects_missing_expected_environment(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EXPECTED_ENVIRONMENT", raising=False)
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    out = rds_query.handler({"confirm": "dev", "sql": "SELECT 1"}, None)
    assert out["ok"] is False


def test_rejects_neither_sql_nor_wipe(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    out = rds_query.handler({"confirm": "dev"}, None)
    assert out["ok"] is False


def test_rejects_wipe_and_sql_together(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    monkeypatch.setenv("ALLOW_CATALOG_WIPE", "true")
    out = rds_query.handler(
        {"confirm": "dev", "wipe_catalog": True, "sql": "SELECT 1"},
        None,
    )
    assert out["ok"] is False
    assert "mutually exclusive" in (out.get("error") or "").lower()


def test_rejects_wipe_without_env_flag(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    monkeypatch.delenv("ALLOW_CATALOG_WIPE", raising=False)
    out = rds_query.handler({"confirm": "dev", "wipe_catalog": True}, None)
    assert out["ok"] is False
    assert "ALLOW_CATALOG_WIPE" in (out.get("error") or "")


def test_wipe_happy_path(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:aws:secretsmanager:eu-west-1:123:secret:x")
    monkeypatch.setenv("ALLOW_CATALOG_WIPE", "true")

    sm = MagicMock()
    sm.get_secret_value.return_value = {
        "SecretString": json.dumps(
            {
                "host": "db.local",
                "port": 5432,
                "username": "u",
                "password": "p",
                "dbname": "streammycourse",
            }
        )
    }
    fake_boto = MagicMock()
    fake_boto.client.return_value = sm

    cur = MagicMock()
    cur.fetchone.side_effect = [(2,), (3,), (1,), (4,), (0,), (0,), (0,), (0,)]
    cursor_cm = MagicMock()
    cursor_cm.__enter__.return_value = cur
    cursor_cm.__exit__.return_value = None

    conn = MagicMock()
    conn.cursor.return_value = cursor_cm

    monkeypatch.setattr(rds_query.boto3, "client", fake_boto.client)
    monkeypatch.setattr(rds_query.psycopg2, "connect", MagicMock(return_value=conn))

    out = rds_query.handler({"confirm": "dev", "wipe_catalog": True}, None)
    assert out["ok"] is True
    assert out["mode"] == "wipe_catalog"
    assert out["counts_before"] == {
        "enrollments": 2,
        "lessons": 3,
        "courses": 1,
        "users": 4,
    }
    assert out["counts_after"] == {
        "enrollments": 0,
        "lessons": 0,
        "courses": 0,
        "users": 0,
    }
    truncate_calls = [
        c for c in cur.execute.call_args_list if "TRUNCATE" in c[0][0].upper()
    ]
    assert len(truncate_calls) == 1
    conn.commit.assert_called_once()
    conn.close.assert_called_once()


def test_read_sql_happy_path(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:aws:secretsmanager:eu-west-1:123:secret:x")

    sm = MagicMock()
    sm.get_secret_value.return_value = {
        "SecretString": json.dumps(
            {
                "host": "db.local",
                "port": 5432,
                "username": "u",
                "password": "p",
                "dbname": "streammycourse",
            }
        )
    }
    fake_boto = MagicMock()
    fake_boto.client.return_value = sm

    cur = MagicMock()
    cur.description = [("n",)]
    cur.fetchmany.return_value = [(1,)]
    cursor_cm = MagicMock()
    cursor_cm.__enter__.return_value = cur
    cursor_cm.__exit__.return_value = None

    conn = MagicMock()
    conn.cursor.return_value = cursor_cm

    monkeypatch.setattr(rds_query.boto3, "client", fake_boto.client)
    monkeypatch.setattr(rds_query.psycopg2, "connect", MagicMock(return_value=conn))

    out = rds_query.handler({"confirm": "dev", "sql": "SELECT 1 AS n"}, None)
    assert out["ok"] is True
    assert out["mode"] == "read"
    assert out["rows"] == [{"n": 1}]
    conn.commit.assert_called_once()


def test_rejects_mutating_sql_without_flags(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    monkeypatch.delenv("ALLOW_MUTATING_SQL", raising=False)
    out = rds_query.handler({"confirm": "dev", "sql": "DELETE FROM users WHERE false"}, None)
    assert out["ok"] is False


def test_mutating_sql_with_flags(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:aws:secretsmanager:eu-west-1:123:secret:x")
    monkeypatch.setenv("ALLOW_MUTATING_SQL", "true")

    sm = MagicMock()
    sm.get_secret_value.return_value = {
        "SecretString": json.dumps(
            {
                "host": "db.local",
                "port": 5432,
                "username": "u",
                "password": "p",
                "dbname": "streammycourse",
            }
        )
    }
    fake_boto = MagicMock()
    fake_boto.client.return_value = sm

    cur = MagicMock()
    cur.rowcount = 0
    cursor_cm = MagicMock()
    cursor_cm.__enter__.return_value = cur
    cursor_cm.__exit__.return_value = None

    conn = MagicMock()
    conn.cursor.return_value = cursor_cm

    monkeypatch.setattr(rds_query.boto3, "client", fake_boto.client)
    monkeypatch.setattr(rds_query.psycopg2, "connect", MagicMock(return_value=conn))

    out = rds_query.handler(
        {
            "confirm": "dev",
            "sql": "DELETE FROM users WHERE false",
            "allow_mutating_sql": True,
        },
        None,
    )
    assert out["ok"] is True
    assert out["mode"] == "mutating"
    assert out.get("rowcount") == 0
    conn.commit.assert_called_once()


def test_rejects_multi_statement_sql(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    out = rds_query.handler({"confirm": "dev", "sql": "SELECT 1; SELECT 2"}, None)
    assert out["ok"] is False


def test_rejects_cte_delete_on_read_path(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    """WITH ... DELETE must not run as read-only (no mutating flags)."""
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    sql = "WITH d AS (DELETE FROM users WHERE false) SELECT 1 AS n"
    out = rds_query.handler({"confirm": "dev", "sql": sql}, None)
    assert out["ok"] is False
    assert "not allowed on the read path" in (out.get("error") or "").lower()


def test_rejects_cte_update_on_read_path(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    sql = "WITH u AS (UPDATE users SET display_name = display_name WHERE false) SELECT 1"
    out = rds_query.handler({"confirm": "dev", "sql": sql}, None)
    assert out["ok"] is False
    assert "not allowed on the read path" in (out.get("error") or "").lower()


def test_rejects_select_into_on_read_path(rds_query, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXPECTED_ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    sql = "SELECT 1 AS n INTO TEMPORARY TABLE tmp_rds_query_guard_test"
    out = rds_query.handler({"confirm": "dev", "sql": sql}, None)
    assert out["ok"] is False
    assert "not allowed on the read path" in (out.get("error") or "").lower()


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "  select 2",
        "WITH t AS (SELECT 1) SELECT * FROM t",
        "EXPLAIN SELECT 1",
        "SHOW search_path",
        "TABLE users",
    ],
)
def test_sql_looks_read_only(rds_query, sql: str) -> None:
    assert rds_query.sql_looks_read_only(sql) is True


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM users",
        "UPDATE users SET x=1",
        "INSERT INTO users VALUES (1)",
        "TRUNCATE users",
    ],
)
def test_sql_not_read_only(rds_query, sql: str) -> None:
    assert rds_query.sql_looks_read_only(sql) is False
