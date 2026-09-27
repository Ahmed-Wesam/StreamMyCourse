"""RS-5 Slice B: migration 015 one-time purchases (courses price, bundle, purchases DDL)."""

from __future__ import annotations

import hashlib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_MIGRATIONS = _ROOT / "infrastructure" / "database" / "migrations"
_MIGRATION = _MIGRATIONS / "015_one_time_purchases.sql"
_MIGRATION_011 = _MIGRATIONS / "011_billing_subscription.sql"
_MIGRATION_012 = _MIGRATIONS / "012_billing_plan_price_50_jod.sql"

# Frozen at RS-5 Slice B — migration 015 must not rewrite earlier billing migrations.
_MIGRATION_011_SHA256 = hashlib.sha256(_MIGRATION_011.read_bytes()).hexdigest()
_MIGRATION_012_SHA256 = hashlib.sha256(_MIGRATION_012.read_bytes()).hexdigest()


def test_migration_015_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_011_and_012_files_unchanged_by_slice_b() -> None:
    assert hashlib.sha256(_MIGRATION_011.read_bytes()).hexdigest() == _MIGRATION_011_SHA256
    assert hashlib.sha256(_MIGRATION_012.read_bytes()).hexdigest() == _MIGRATION_012_SHA256


def test_migration_015_one_time_purchases_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()

    assert "price_amount_minor" in lowered
    assert "alter table courses" in lowered
    assert "integer" in lowered

    assert "create table if not exists bundle_offers" in lowered
    assert "environment" in lowered
    assert "amount_minor" in lowered
    assert "'usd'" in lowered or "default 'usd'" in lowered

    assert "create table if not exists purchases" in lowered
    assert "product_type" in lowered
    assert "'course'" in sql
    assert "'bundle'" in sql
    assert "course_id" in lowered
    assert "status" in lowered
    assert "'pending'" in sql
    assert "'paid'" in sql
    assert "'revoked'" in sql
    assert "'failed'" in sql
    assert "provider_tran_ref" in lowered
    assert "cart_id" in lowered
    assert "user_sub" in lowered

    assert "uq_purchases_one_paid_course_per_user_course_env" in lowered
    assert "uq_purchases_one_paid_bundle_per_user_env" in lowered
    assert "where" in lowered and "status = 'paid'" in lowered

    assert "references courses" in lowered
    purchases_fk_chunk = lowered.split("purchases")[1] if "purchases" in lowered else lowered
    assert "on delete cascade" not in purchases_fk_chunk.split("drop table")[0]

    assert "drop table if exists user_subscriptions" in lowered
    assert "drop table if exists subscription_plans" in lowered

    assert "011_billing_subscription.sql" not in sql
    assert "012_billing_plan_price_50_jod.sql" not in sql
