"""RS-11 Slice 1: migration 019 lesson_files and lesson_notes."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "019_lesson_files_and_notes.sql"
)


def test_migration_019_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_019_lesson_files_and_notes_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "create table" in lowered and "lesson_files" in lowered
    assert "create table" in lowered and "lesson_notes" in lowered
    assert "foreign key (course_id, lesson_id) references lessons" in lowered.replace(
        "  ", " "
    ) or "references lessons (course_id, id)" in lowered
    assert "user_sub" in lowered
    assert "idx_lesson_notes_user_lesson" in lowered or "user_sub, lesson_id" in lowered
    compact = lowered.replace(" ", "")
    assert "kind" in lowered
    assert "status" in lowered
    assert "pending" in lowered or "ready" in lowered
