"""DSQL-3 S4: partial async index on lessons.video_key (plans/dsql-ws3-course-catalog.md)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DSQL_DIR = _ROOT / "infrastructure" / "database" / "dsql"
_MIGRATION_0002 = _DSQL_DIR / "0002_lesson_video_key_index.sql"
_APPLIER = _ROOT / "scripts" / "apply-dsql-schema.py"


def _load_applier():
    spec = importlib.util.spec_from_file_location("apply_dsql_schema_s4", _APPLIER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_0002_migration_file_exists_with_async_partial_index() -> None:
    assert _MIGRATION_0002.is_file(), f"missing {_MIGRATION_0002}"
    sql = _MIGRATION_0002.read_text(encoding="utf-8")
    assert re.search(r"CREATE\s+INDEX\s+ASYNC", sql, re.IGNORECASE), sql
    assert re.search(r"WHERE\s+video_key\s+<>\s+''", sql, re.IGNORECASE), sql
    assert "idx_lessons_video_key" in sql
    assert "app.lessons" in sql


def test_applier_discovers_0002_after_0001() -> None:
    applier = _load_applier()
    assert hasattr(applier, "ordered_migration_sql_files"), (
        "apply-dsql-schema.py must expose ordered_migration_sql_files for incremental DDL"
    )
    paths = applier.ordered_migration_sql_files(_DSQL_DIR)
    versions = [applier.migration_version_from_path(p) for p in paths]
    assert versions == sorted(versions)
    assert "0001" in versions and "0002" in versions
    assert versions.index("0001") < versions.index("0002")
    assert paths[-1].name == "0005_dev_bundle_offer.sql"
