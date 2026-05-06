"""Unit tests for the RDS schema-applier Lambda (SQL splitting only).

The handler lives under ``infrastructure/lambda/`` (outside the catalog package) so
we load it by path to avoid coupling the catalog test tree to that layout."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_INDEX = _ROOT / "infrastructure" / "lambda" / "rds_schema_apply" / "index.py"


@pytest.fixture(scope="module")
def schema_apply():
    spec = importlib.util.spec_from_file_location("rds_schema_apply_index", _INDEX)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_split_sql_strips_full_line_comments(schema_apply):
    sql = """-- leading
CREATE TABLE IF NOT EXISTS a (id INT);
-- between
CREATE TABLE IF NOT EXISTS b (id INT);
"""
    parts = schema_apply._split_sql_statements(sql)
    assert len(parts) == 2
    assert "CREATE TABLE IF NOT EXISTS a" in parts[0]
    assert "CREATE TABLE IF NOT EXISTS b" in parts[1]


def test_split_sql_empty_and_whitespace(schema_apply):
    assert schema_apply._split_sql_statements("") == []
    assert schema_apply._split_sql_statements("   \n  -- only comment\n") == []


def test_split_real_migration_file_contains_expected_ddl(schema_apply):
    """001_initial_schema.sql is the bundled schema; split/join must surface all core DDL including lesson_progress."""
    path = _ROOT / "infrastructure" / "database" / "migrations" / "001_initial_schema.sql"
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "CREATE EXTENSION IF NOT EXISTS" in joined
    assert "CREATE TABLE IF NOT EXISTS users" in joined
    assert "CREATE TABLE IF NOT EXISTS courses" in joined
    assert "CREATE TABLE IF NOT EXISTS lessons" in joined
    assert "CREATE TABLE IF NOT EXISTS enrollments" in joined
    assert "CREATE TABLE IF NOT EXISTS lesson_progress" in joined
    assert "user_sub" in joined
    assert "lesson_id" in joined
    assert "completed" in joined
    assert "completed_at" in joined
    assert "last_position_sec" in joined
    assert "updated_at" in joined
    assert "REFERENCES users(user_sub)" in joined
    assert "REFERENCES lessons(id)" in joined
    assert "REFERENCES courses(id)" in joined
    assert "CREATE INDEX IF NOT EXISTS idx_lesson_progress_course_user" in joined
    assert "PRIMARY KEY (user_sub, lesson_id)" in joined
    assert "CONSTRAINT chk_lesson_progress_position_nonneg" in joined
    assert len(parts) >= 11


def test_handler_returns_error_when_secret_arn_missing(schema_apply, monkeypatch) -> None:
    monkeypatch.delenv("SECRET_ARN", raising=False)
    out = schema_apply.handler({}, MagicMock(aws_request_id=""))
    assert out == {"ok": False, "error": "SECRET_ARN is not set"}


def test_handler_returns_error_when_schema_file_missing(schema_apply, monkeypatch) -> None:
    """The repo checkout may not ship ``schema.sql`` beside ``index.py``; handler must fail clearly."""
    monkeypatch.setenv("SECRET_ARN", "arn:aws:secretsmanager:us-east-1:1:secret:x")
    out = schema_apply.handler({}, MagicMock(aws_request_id="rid"))
    assert out["ok"] is False
    assert "schema.sql missing" in str(out.get("error", ""))


def test_handler_applies_schema_and_commits(schema_apply, monkeypatch, tmp_path) -> None:
    # Avoid writing into the repo tree: point __file__ at a temp dir so the handler
    # resolves schema.sql relative to tmp_path instead of infrastructure/lambda/.
    monkeypatch.setattr(schema_apply, "__file__", str(tmp_path / "index.py"))
    schema_file = tmp_path / "schema.sql"
    schema_file.write_text("-- comment line\nCREATE TABLE IF NOT EXISTS _unit (id INT);\n", encoding="utf-8")
    monkeypatch.setenv(
        "SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123456789:secret:rds/schema"
    )
    secret = {
        "host": "db.example",
        "port": 5432,
        "username": "u",
        "password": "p",
        "dbname": "app",
    }
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cur

    with (
        patch.object(schema_apply, "boto3") as mock_boto,
        patch.object(schema_apply, "psycopg2") as mock_pg,
    ):
        mock_boto.client.return_value.get_secret_value.return_value = {
            "SecretString": json.dumps(secret),
        }
        mock_pg.connect.return_value = mock_conn
        mock_pg.Error = Exception

        out = schema_apply.handler({"debug": True}, MagicMock(aws_request_id="rid"))

    assert out == {"ok": True}
    mock_pg.connect.assert_called_once()
    assert mock_cur.execute.call_count >= 1
    args = [c[0][0] for c in mock_cur.execute.call_args_list]
    assert any("CREATE TABLE" in str(s) for s in args)
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()


def test_handler_rollback_on_statement_error(schema_apply, monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(schema_apply, "__file__", str(tmp_path / "index.py"))
    schema_file = tmp_path / "schema.sql"
    schema_file.write_text("SELECT 1;\nSELECT 2;\n", encoding="utf-8")
    monkeypatch.setenv("SECRET_ARN", "arn:x")
    secret = {
        "host": "h",
        "port": 5432,
        "username": "u",
        "password": "p",
        "dbname": "d",
    }

    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_cur.__enter__ = MagicMock(return_value=mock_cur)
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cur

    with (
        patch.object(schema_apply, "boto3") as mock_boto,
        patch.object(schema_apply, "psycopg2") as mock_pg,
    ):
        PgErr = type("PgErr", (Exception,), {})
        mock_pg.Error = PgErr
        mock_cur.execute.side_effect = PgErr("stmt failed")
        mock_boto.client.return_value.get_secret_value.return_value = {
            "SecretString": json.dumps(secret),
        }
        mock_pg.connect.return_value = mock_conn

        out = schema_apply.handler({}, MagicMock(aws_request_id=""))

    assert out["ok"] is False
    assert "stmt failed" in str(out.get("error", ""))
    mock_conn.rollback.assert_called_once()
    mock_conn.close.assert_called_once()
