"""RS-16: migration 023 lesson transcript, activity days, and user preferences."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "023_rs16_learning_features.sql"
)


def test_migration_023_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_023_learning_features_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    compact = " ".join(lowered.split())

    assert "alter table lessons" in compact
    assert "transcript" in lowered
    assert "text" in lowered

    assert "learning_activity_days" in lowered
    assert "user_sub" in lowered
    assert "day" in lowered
    assert "date" in lowered
    assert "primary key" in compact

    assert "pref_autoplay_next" in lowered
    assert "pref_auto_mark_complete" in lowered
    assert "pref_progress_celebrations" in lowered
    assert "boolean" in lowered
    assert "research_interest_tags" in lowered
    assert "text[]" in lowered
    assert "last_login_at" in lowered
    assert "timestamptz" in lowered
    assert "research_interests" not in compact or "research_interest_tags" in lowered
