"""RS-8 Slice 2: migration 018 module_quizzes.pass_percent."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "018_module_quiz_pass_percent.sql"
)


def test_migration_018_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_018_pass_percent_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "alter table module_quizzes" in lowered
    assert "pass_percent" in lowered
    assert "default 70" in lowered
    compact = lowered.replace(" ", "")
    assert "pass_percent>=1" in compact
    assert "pass_percent<=100" in compact
