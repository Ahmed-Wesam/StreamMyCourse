"""W6-P0: migration 012 sets monthly_all_access plan price to 50 JOD (50000 fils)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "012_billing_plan_price_50_jod.sql"
)


def test_migration_012_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_012_updates_monthly_all_access_to_50000_fils() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    assert "update" in lowered
    assert "subscription_plans" in lowered
    assert "amount_minor" in lowered
    assert "50000" in sql
    assert "monthly_all_access" in sql
    assert "plan_key" in lowered
