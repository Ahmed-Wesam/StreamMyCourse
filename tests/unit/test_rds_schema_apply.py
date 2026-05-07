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
    assert "UNIQUE (course_id, id)" in joined
    # The composite FK on lesson_progress must be named explicitly so 003 can
    # drop+re-add it idempotently by a stable name on fresh and existing DBs.
    assert (
        "CONSTRAINT lesson_progress_course_lesson_fkey FOREIGN KEY (course_id, lesson_id) REFERENCES lessons"
        in joined
    )
    assert "REFERENCES lessons (course_id, id)" in joined
    assert "REFERENCES courses(id)" in joined
    assert "CREATE INDEX IF NOT EXISTS idx_lesson_progress_course_user" in joined
    assert "PRIMARY KEY (user_sub, lesson_id)" in joined
    assert "CONSTRAINT chk_lesson_progress_position_nonneg" in joined
    assert len(parts) >= 11


def test_split_real_migration_003_contains_expected_upgrade_ddl(schema_apply):
    """003_progress_course_lesson_fk.sql is the in-place upgrade bundled alongside
    001 (see scripts/deploy-rds-stack.sh and .github/workflows/deploy-backend.yml).

    The schema-applier Lambda's ``_split_sql_statements`` is a naive ``;`` split,
    so 003 must contain only plain DDL — no ``DO $$ ... $$;`` blocks. This test
    verifies the file remains splitter-safe and idempotent (DROP IF EXISTS + ADD).
    """
    path = (
        _ROOT
        / "infrastructure"
        / "database"
        / "migrations"
        / "003_progress_course_lesson_fk.sql"
    )
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "CREATE UNIQUE INDEX IF NOT EXISTS lessons_course_id_id_key" in joined
    assert "DROP CONSTRAINT IF EXISTS lesson_progress_lesson_id_fkey" in joined
    assert "DROP CONSTRAINT IF EXISTS lesson_progress_course_lesson_fkey" in joined
    assert "ADD CONSTRAINT lesson_progress_course_lesson_fkey" in joined
    assert "FOREIGN KEY (course_id, lesson_id)" in joined
    assert "REFERENCES lessons (course_id, id)" in joined
    assert "ON DELETE CASCADE" in joined
    # Splitter-safety: the executable SQL (post-comment-strip) must not
    # introduce DO blocks, which would fool the naive `;` split because they
    # contain inner `;` characters. Comment-only mentions of "DO $$" in the
    # file header are fine; they get stripped by `_split_sql_statements`.
    executable_sql = "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )
    assert "DO $$" not in executable_sql
    assert len(parts) == 4


def test_concatenated_001_and_003_bundle_is_splittable_and_complete(schema_apply):
    """The deploy script and CI workflow concatenate 001 and 003 into a single
    schema.sql before zipping the Lambda. Verify the concatenation is splittable
    end-to-end and surfaces both the canonical schema and the upgrade DDL.
    """
    migrations_dir = _ROOT / "infrastructure" / "database" / "migrations"
    sql_001 = (migrations_dir / "001_initial_schema.sql").read_text(encoding="utf-8")
    sql_003 = (migrations_dir / "003_progress_course_lesson_fk.sql").read_text(
        encoding="utf-8"
    )
    bundle = sql_001 + sql_003
    parts = schema_apply._split_sql_statements(bundle)
    joined = "\n".join(parts)
    # 001 markers
    assert "CREATE TABLE IF NOT EXISTS lesson_progress" in joined
    # 003 markers
    assert "CREATE UNIQUE INDEX IF NOT EXISTS lessons_course_id_id_key" in joined
    assert "DROP CONSTRAINT IF EXISTS lesson_progress_lesson_id_fkey" in joined
    assert "ADD CONSTRAINT lesson_progress_course_lesson_fkey" in joined
    # Sanity: 001 alone gave >=11 statements; 003 adds 4 more.
    assert len(parts) >= 15


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
