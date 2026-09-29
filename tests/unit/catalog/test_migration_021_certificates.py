"""RS-12: migration 021 certificate_code + certificates table."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "021_certificates.sql"
)


def test_migration_021_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_021_certificates_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    compact = " ".join(lowered.split())

    assert "certificate_code" in lowered
    assert "unique" in lowered
    assert "create table" in lowered and "certificates" in lowered
    assert "credential_id" in lowered
    assert (
        "unique (user_sub, course_id)" in compact
        or "unique(user_sub, course_id)" in compact
        or "unique (user_sub,course_id)" in compact
    )
    assert "valid" in lowered and "revoked" in lowered
    assert "check" in lowered and "status" in lowered
