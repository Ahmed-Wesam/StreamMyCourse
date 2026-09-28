"""RS-7 Slice A: migration 017 courses.page_content JSONB."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = _ROOT / "infrastructure" / "database" / "migrations" / "017_course_page_content.sql"


def test_migration_017_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_017_course_page_content_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "alter table courses" in lowered
    assert "page_content" in lowered
    assert "jsonb" in lowered
    assert "default" in lowered and "'{}'" in sql
