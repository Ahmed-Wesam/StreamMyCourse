"""DDL presence tests for QB-A (006) and QB-C questions (007) migrations."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _ROOT / "infrastructure" / "database" / "migrations" / "006_question_banks_module_quizzes.sql"
_MIGRATION_007 = _ROOT / "infrastructure" / "database" / "migrations" / "007_question_bank_questions.sql"
_MIGRATION_008 = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "008_student_module_quiz_bindings.sql"
)
_MIGRATION_009 = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "009_module_quiz_attempts.sql"
)
_MIGRATION_010 = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "010_module_quiz_attempt_submissions.sql"
)
_DEPLOY_BACKEND = _ROOT / ".github" / "workflows" / "deploy-backend.yml"


def test_006_migration_file_exists_and_encodes_cardinality() -> None:
    assert _MIGRATION.is_file(), "expected 006_question_banks_module_quizzes.sql in repo"
    text = _MIGRATION.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS question_banks" in text
    assert "CREATE TABLE IF NOT EXISTS module_quizzes" in text
    assert "UNIQUE (module_id)" in text
    assert "REFERENCES courses(id)" in text
    assert (
        "FOREIGN KEY (course_id, question_bank_id) REFERENCES question_banks (course_id, id)"
        in text
    )
    assert "module_quizzes_served_count_n_positive" in text
    assert "CHECK (served_count_n IS NULL OR served_count_n >= 1)" in text


def test_007_migration_file_exists_and_questions_table() -> None:
    assert _MIGRATION_007.is_file(), "expected 007_question_bank_questions.sql in repo"
    text = _MIGRATION_007.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS questions" in text
    assert "REFERENCES courses(id)" in text
    assert (
        "FOREIGN KEY (course_id, question_bank_id) REFERENCES question_banks (course_id, id)"
        in text
    )
    assert "questions_status_valid" in text
    assert "CHECK (status IN ('DRAFT', 'PUBLISHED'))" in text
    assert "options_json" in text and "JSONB" in text
    assert "correct_option_key" in text


def test_008_migration_file_exists_and_binding_tables() -> None:
    assert _MIGRATION_008.is_file(), (
        "expected 008_student_module_quiz_bindings.sql in repo"
    )
    text = _MIGRATION_008.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS student_module_quiz_bindings" in text
    assert "CREATE TABLE IF NOT EXISTS student_module_quiz_binding_questions" in text
    assert "UNIQUE (module_quiz_id, user_sub)" in text
    assert "user_sub VARCHAR(255)" in text
    assert "REFERENCES module_quizzes" in text
    assert "REFERENCES questions(id) ON DELETE CASCADE" in text
    assert "ALTER TABLE" not in text
    assert "DROP CONSTRAINT" not in text


def test_009_migration_file_exists_and_attempt_table() -> None:
    assert _MIGRATION_009.is_file(), (
        "expected 009_module_quiz_attempts.sql in repo"
    )
    text = _MIGRATION_009.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS module_quiz_attempts" in text
    assert "binding_id" in text
    assert "REFERENCES student_module_quiz_bindings" in text
    assert "attempt_number" in text
    assert "UNIQUE (binding_id, attempt_number)" in text
    assert "CHECK (attempt_number >= 1)" in text
    assert "CHECK (status IN ('in_progress', 'submitted'))" in text
    assert "shuffled_question_order" in text and "JSONB" in text
    assert "shuffled_choice_orders" in text and "JSONB" in text
    assert "jsonb_typeof(shuffled_question_order) = 'array'" in text
    assert "jsonb_typeof(shuffled_choice_orders) = 'object'" in text
    assert "uq_module_quiz_attempts_one_in_progress" in text
    assert "WHERE status = 'in_progress'" in text
    assert "ALTER TABLE" not in text
    assert "DROP CONSTRAINT" not in text


def test_009_migration_listed_in_deploy_backend_workflow() -> None:
    assert _DEPLOY_BACKEND.is_file()
    text = _DEPLOY_BACKEND.read_text(encoding="utf-8")
    assert "009_module_quiz_attempts.sql" in text


def test_010_migration_file_exists_and_submission_table() -> None:
    assert _MIGRATION_010.is_file(), (
        "expected 010_module_quiz_attempt_submissions.sql in repo"
    )
    text = _MIGRATION_010.read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS module_quiz_attempt_submissions" in text
    assert "answers_json     JSONB NOT NULL" in text
    assert "correct_count    INTEGER NOT NULL" in text
    assert "total_count      INTEGER NOT NULL" in text
    assert "submitted_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()" in text
    assert "REFERENCES module_quiz_attempts(id) ON DELETE CASCADE" in text
    assert "CHECK (jsonb_typeof(answers_json) = 'object')" in text
    assert "CHECK (total_count >= 1)" in text
    assert "CHECK (correct_count >= 0)" in text
    assert "CHECK (correct_count <= total_count)" in text
    assert "PRIMARY KEY" in text and "attempt_id" in text
    assert "ALTER TABLE" not in text
    assert "DROP CONSTRAINT" not in text


def test_010_migration_listed_in_deploy_backend_workflow() -> None:
    assert _DEPLOY_BACKEND.is_file()
    text = _DEPLOY_BACKEND.read_text(encoding="utf-8")
    assert "010_module_quiz_attempt_submissions.sql" in text
