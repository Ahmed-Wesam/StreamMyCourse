"""RS-6 Slice A: migration 016 user profile columns on users."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = _ROOT / "infrastructure" / "database" / "migrations" / "016_user_profile_fields.sql"


def test_migration_016_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_016_user_profile_fields_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()

    assert "alter table users" in lowered
    for col in (
        "given_name",
        "family_name",
        "country",
        "profession",
        "institution",
        "research_interests",
        "terms_accepted_at",
        "privacy_accepted_at",
    ):
        assert col in lowered
