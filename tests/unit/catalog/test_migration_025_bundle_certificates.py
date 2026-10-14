"""Bundle certificates: migration 025 DDL expectations (red until file lands)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "025_bundle_certificates.sql"
)


def test_migration_025_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_025_bundle_certificates_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    compact = " ".join(lowered.split())

    assert "create table" in lowered and "bundle_certificates" in lowered
    assert "credential_id" in lowered
    assert "unique" in lowered
    assert (
        "unique (user_sub)" in compact
        or "unique(user_sub)" in compact
        or "unique (user_sub," in compact
    )
    assert "valid" in lowered and "revoked" in lowered
    assert "check" in lowered and "status" in lowered
