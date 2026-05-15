"""DDL presence tests for QB-A question bank + module quiz migration (006)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = _ROOT / "infrastructure" / "database" / "migrations" / "006_question_banks_module_quizzes.sql"


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
