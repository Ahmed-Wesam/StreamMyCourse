"""DSQL-7b S1: bundle credential expression index (plans/dsql-ws7-assignments-certs-research.md)."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_DSQL_DIR = _ROOT / "infrastructure" / "database" / "dsql"
_MIGRATION_0004 = _DSQL_DIR / "0004_bundle_credential_upper.sql"
_APPLIER = _ROOT / "scripts" / "apply-dsql-schema.py"


def _load_applier():
    spec = importlib.util.spec_from_file_location("apply_dsql_schema_s7b", _APPLIER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_0004_migration_file_bundle_expression_index_and_version() -> None:
    assert _MIGRATION_0004.is_file(), f"missing {_MIGRATION_0004}"
    sql = _MIGRATION_0004.read_text(encoding="utf-8")
    assert re.search(
        r"CREATE\s+UNIQUE\s+INDEX\s+ASYNC\s+bundle_certificates_credential_id_upper",
        sql,
        re.IGNORECASE,
    ), sql
    assert "(upper(credential_id))" in sql or "(upper(credential_id) )" in sql.replace(" ", "")
    assert "app.bundle_certificates" in sql
    assert re.search(
        r"INSERT\s+INTO\s+app\.schema_migrations.*'0004'",
        sql,
        re.IGNORECASE | re.DOTALL,
    ), sql


def test_applier_discovers_0004_after_0003() -> None:
    applier = _load_applier()
    paths = applier.ordered_migration_sql_files(_DSQL_DIR)
    versions = [applier.migration_version_from_path(p) for p in paths]
    assert "0004" in versions
    assert versions.index("0003") < versions.index("0004")
    assert versions.index("0004") < versions.index("0005")
