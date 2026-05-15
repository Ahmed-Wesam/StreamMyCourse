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
    assert "REFERENCES questions" in text
