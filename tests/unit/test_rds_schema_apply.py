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
    assert "created_by     VARCHAR(255) NOT NULL" in joined
    assert "CONSTRAINT courses_created_by_not_blank CHECK (btrim(created_by) <> '')" in joined
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


def test_split_sql_dollar_quote_preserves_inner_semicolons(schema_apply):
    """Semicolons inside $$ ... $$ dollar-quoted blocks must not split the statement."""
    sql = """\
DO $$
DECLARE
    n INT;
BEGIN
    SELECT COUNT(*) INTO n FROM courses;
    IF n > 0 THEN
        RAISE WARNING 'found %', n;
    END IF;
END;
$$;
"""
    parts = schema_apply._split_sql_statements(sql)
    assert len(parts) == 1
    assert "DO $$" in parts[0]
    assert "RAISE WARNING" in parts[0]
    assert parts[0].endswith(";")


def test_split_sql_dollar_quote_mixed_with_plain_statements(schema_apply):
    """Plain DDL before and after a dollar-quoted block should produce 3 statements."""
    sql = """\
ALTER TABLE t ALTER COLUMN c DROP DEFAULT;

DO $$
BEGIN
    RAISE WARNING 'hi';
END;
$$;

ALTER TABLE t ADD CONSTRAINT c_check CHECK (c <> '');
"""
    parts = schema_apply._split_sql_statements(sql)
    assert len(parts) == 3
    assert "ALTER TABLE t ALTER COLUMN" in parts[0]
    assert "DO $$" in parts[1]
    assert "ADD CONSTRAINT c_check" in parts[2]


def test_split_real_migration_003_contains_expected_upgrade_ddl(schema_apply):
    """003_progress_course_lesson_fk.sql is the in-place upgrade bundled alongside
    001 (see scripts/deploy-rds-stack.sh and .github/workflows/deploy-backend.yml).

    Verifies the file is idempotent (DROP IF EXISTS + ADD) and produces the expected
    number of statements when split.
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
    assert len(parts) == 4


def test_split_real_migration_004_contains_expected_upgrade_ddl(schema_apply):
    """004_enforce_course_created_by.sql uses a DO block to apply ADD CONSTRAINT
    safely — skipping with a WARNING if blank-owner rows would cause it to fail.

    The splitter must handle the $$ ... $$ block as a single statement and not
    split on the semicolons inside the PL/pgSQL body.
    """
    path = (
        _ROOT
        / "infrastructure"
        / "database"
        / "migrations"
        / "004_enforce_course_created_by.sql"
    )
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "ALTER COLUMN created_by DROP DEFAULT" in joined
    assert "DROP CONSTRAINT IF EXISTS courses_created_by_not_blank" in joined
    assert "ADD CONSTRAINT courses_created_by_not_blank" in joined
    assert "CHECK (btrim(created_by) <> " in joined
    assert "DO $$" in joined
    assert "RAISE WARNING" in joined
    # 1 plain ALTER TABLE + 1 DO $$ block
    assert len(parts) == 2


def test_split_real_migration_006_contains_expected_qb_a_ddl(schema_apply):
    """006_question_banks_module_quizzes.sql adds QB-A tables and cross-course FK."""
    path = (
        _ROOT
        / "infrastructure"
        / "database"
        / "migrations"
        / "006_question_banks_module_quizzes.sql"
    )
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "CREATE TABLE IF NOT EXISTS question_banks" in joined
    assert "CREATE TABLE IF NOT EXISTS module_quizzes" in joined
    assert "UNIQUE (module_id)" in joined
    assert (
        "FOREIGN KEY (course_id, question_bank_id) REFERENCES question_banks (course_id, id)"
        in joined
    )
    assert len(parts) >= 4


def test_split_real_migration_007_contains_expected_questions_ddl(schema_apply):
    """007_question_bank_questions.sql adds questions with composite bank FK."""
    path = (
        _ROOT
        / "infrastructure"
        / "database"
        / "migrations"
        / "007_question_bank_questions.sql"
    )
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "CREATE TABLE IF NOT EXISTS questions" in joined
    assert (
        "FOREIGN KEY (course_id, question_bank_id) REFERENCES question_banks (course_id, id)"
        in joined
    )
    assert len(parts) >= 3


def test_split_real_migration_008_contains_expected_bindings_ddl(schema_apply):
    """008_student_module_quiz_bindings.sql adds binding tables (idempotent DDL only)."""
    path = (
        _ROOT
        / "infrastructure"
        / "database"
        / "migrations"
        / "008_student_module_quiz_bindings.sql"
    )
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "CREATE TABLE IF NOT EXISTS student_module_quiz_bindings" in joined
    assert "CREATE TABLE IF NOT EXISTS student_module_quiz_binding_questions" in joined
    assert "ON DELETE CASCADE" in joined
    assert "ALTER TABLE" not in joined
    assert len(parts) >= 4


def test_split_real_migration_011_contains_expected_billing_ddl(schema_apply):
    """011_billing_subscription.sql adds billing tables (idempotent DDL only)."""
    path = (
        _ROOT
        / "infrastructure"
        / "database"
        / "migrations"
        / "011_billing_subscription.sql"
    )
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "CREATE TABLE IF NOT EXISTS subscription_plans" in joined
    assert "CREATE TABLE IF NOT EXISTS teacher_merchant_accounts" in joined
    assert "CREATE TABLE IF NOT EXISTS user_subscriptions" in joined
    assert "CREATE TABLE IF NOT EXISTS payment_webhook_events" in joined
    assert "UNIQUE (environment, plan_key)" in joined
    assert "UNIQUE (id, environment)" in joined
    assert (
        "CHECK (status IN ('active', 'past_due', 'canceled', 'expired', 'incomplete'))"
        in joined
    )
    assert "user_subscriptions_plan_environment_fkey" in joined
    assert (
        "FOREIGN KEY (plan_id, environment) REFERENCES subscription_plans (id, environment)"
        in joined
    )
    assert "uq_user_subscriptions_one_granting_per_user_env" in joined
    assert "WHERE status IN ('active', 'past_due', 'incomplete')" in joined
    assert "uq_user_subscriptions_provider_subscription_id" in joined
    assert "WHERE provider_subscription_id IS NOT NULL" in joined
    assert "UNIQUE (provider, provider_event_id)" in joined
    assert "INSERT INTO subscription_plans" in joined
    assert "'monthly_all_access'" in joined
    assert "'JOD'" in joined
    assert "9990" in joined
    assert "amount_minor" in joined
    # fils documented on full-line comment (stripped by applier splitter — no inline ';' in DDL)
    assert "fils" in sql.lower()
    assert "REFERENCES users(user_sub)" in joined
    assert "ON CONFLICT (environment, plan_key) DO NOTHING" in joined
    assert len(parts) >= 8


def test_deploy_backend_bundles_migration_011() -> None:
    """deploy-backend.yml must cat 011 into both dev and prod schema-applier bundles."""
    path = _ROOT / ".github" / "workflows" / "deploy-backend.yml"
    text = path.read_text(encoding="utf-8")
    needle = "011_billing_subscription.sql"
    for marker in ("rds-schema-apply-dev-", "rds-schema-apply-prod-"):
        start = text.index(marker)
        end = text.index('> "$PKG/schema.sql"', start)
        chunk = text[start:end]
        assert needle in chunk
        assert "010_module_quiz_attempt_submissions.sql" in chunk
        assert chunk.index("010_module_quiz_attempt_submissions.sql") < chunk.index(needle)


def test_deploy_rds_stack_sh_bundles_migration_011() -> None:
    """scripts/deploy-rds-stack.sh must cat 011 after 010 in the local schema bundle."""
    path = _ROOT / "scripts" / "deploy-rds-stack.sh"
    text = path.read_text(encoding="utf-8")
    needle = "011_billing_subscription.sql"
    start = text.index("cat \\")
    end = text.index('> "$PKG/schema.sql"', start)
    chunk = text[start:end]
    assert needle in chunk
    assert "010_module_quiz_attempt_submissions.sql" in chunk
    assert chunk.index("010_module_quiz_attempt_submissions.sql") < chunk.index(needle)


def test_deploy_ps1_lists_migration_011() -> None:
    """infrastructure/deploy.ps1 schema bundle must include 011 after 010."""
    path = _ROOT / "infrastructure" / "deploy.ps1"
    text = path.read_text(encoding="utf-8")
    needle = "011_billing_subscription.sql"
    start = text.index("$schemaSqlFiles = @(")
    end = text.index(")", start)
    chunk = text[start:end]
    assert needle in chunk
    assert "010_module_quiz_attempt_submissions.sql" in chunk
    assert chunk.index("010_module_quiz_attempt_submissions.sql") < chunk.index(needle)


def test_concatenated_001_003_004_006_007_008_bundle_is_splittable_and_complete(schema_apply):
    """Deploy script and CI concatenate 001, 003, 004, 006, 007, and 008 into schema.sql."""
    migrations_dir = _ROOT / "infrastructure" / "database" / "migrations"
    sql_001 = (migrations_dir / "001_initial_schema.sql").read_text(encoding="utf-8")
    sql_003 = (migrations_dir / "003_progress_course_lesson_fk.sql").read_text(
        encoding="utf-8"
    )
    sql_004 = (migrations_dir / "004_enforce_course_created_by.sql").read_text(
        encoding="utf-8"
    )
    sql_006 = (migrations_dir / "006_question_banks_module_quizzes.sql").read_text(
        encoding="utf-8"
    )
    sql_007 = (migrations_dir / "007_question_bank_questions.sql").read_text(
        encoding="utf-8"
    )
    sql_008 = (migrations_dir / "008_student_module_quiz_bindings.sql").read_text(
        encoding="utf-8"
    )
    bundle = sql_001 + sql_003 + sql_004 + sql_006 + sql_007 + sql_008
    parts = schema_apply._split_sql_statements(bundle)
    joined = "\n".join(parts)
    # 001 markers
    assert "CREATE TABLE IF NOT EXISTS lesson_progress" in joined
    # 003 markers
    assert "CREATE UNIQUE INDEX IF NOT EXISTS lessons_course_id_id_key" in joined
    assert "DROP CONSTRAINT IF EXISTS lesson_progress_lesson_id_fkey" in joined
    assert "ADD CONSTRAINT lesson_progress_course_lesson_fkey" in joined
    # 004 markers
    assert "ALTER COLUMN created_by DROP DEFAULT" in joined
    assert "ADD CONSTRAINT courses_created_by_not_blank" in joined
    # 006 markers (QB-A)
    assert "CREATE TABLE IF NOT EXISTS question_banks" in joined
    assert "CREATE TABLE IF NOT EXISTS module_quizzes" in joined
    assert "UNIQUE (module_id)" in joined
    # 007 markers (QB-C)
    assert "CREATE TABLE IF NOT EXISTS questions" in joined
    assert "options_json" in joined
    # 008 markers (QB-F bindings)
    assert "CREATE TABLE IF NOT EXISTS student_module_quiz_bindings" in joined
    assert "CREATE TABLE IF NOT EXISTS student_module_quiz_binding_questions" in joined
    # Sanity: 001 >=11; 003 adds 4; 004 adds 2; 006 + 007 + 008 add CREATE/INDEX statements.
    assert len(parts) >= 32


def test_concatenated_deploy_schema_bundle_through_011_is_splittable(schema_apply):
    """CI deploy-backend.yml concatenates 001–011 (skipping 002/005) into schema.sql."""
    migrations_dir = _ROOT / "infrastructure" / "database" / "migrations"
    names = (
        "001_initial_schema.sql",
        "003_progress_course_lesson_fk.sql",
        "004_enforce_course_created_by.sql",
        "006_question_banks_module_quizzes.sql",
        "007_question_bank_questions.sql",
        "008_student_module_quiz_bindings.sql",
        "009_module_quiz_attempts.sql",
        "010_module_quiz_attempt_submissions.sql",
        "011_billing_subscription.sql",
    )
    bundle = "".join((migrations_dir / n).read_text(encoding="utf-8") for n in names)
    parts = schema_apply._split_sql_statements(bundle)
    joined = "\n".join(parts)
    assert "CREATE TABLE IF NOT EXISTS module_quiz_attempt_submissions" in joined
    assert "CREATE TABLE IF NOT EXISTS subscription_plans" in joined
    assert "CREATE TABLE IF NOT EXISTS user_subscriptions" in joined
    assert len(parts) >= 40


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
    # Schema apply must SET lock_timeout before any DDL so a held AccessShareLock
    # surfaces as a fast `lock_timeout` error (clear stack pointing at the
    # blocked statement) instead of silently consuming the Lambda runtime.
    assert any("SET lock_timeout" in str(s) for s in args)
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
