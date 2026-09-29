"""RS-14: migration 022 research team tables + partial unique index."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "022_research_team.sql"
)


def test_migration_022_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_022_research_team_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    compact = " ".join(lowered.split())

    assert "research_team_required_courses" in lowered
    assert "research_team_applications" in lowered
    assert "create unique index" in compact
    assert "research_team_applications_one_open" in lowered
    assert "research_team_applications_one_accepted" in lowered
    assert "where status in ('submitted', 'under_review')" in compact or (
        "where status in ('submitted','under_review')" in compact
    )
    assert "where status = 'accepted'" in compact or 'where status = "accepted"' in compact
    assert "submitted" in lowered and "under_review" in lowered
    assert "accepted" in lowered and "rejected" in lowered
    assert "reapply_allowed" in lowered
