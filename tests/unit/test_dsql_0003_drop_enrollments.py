"""DSQL-4 S1: drop enrollments migration and orphan-audit FK pairs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_DSQL_DIR = _REPO / "infrastructure" / "database" / "dsql"
_MIGRATION_0003 = _DSQL_DIR / "0003_drop_enrollments.sql"
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dsql_fk_pairs import DSQL_FOREIGN_KEY_EDGES  # noqa: E402


def test_0003_migration_file_drops_enrollments_and_records_version() -> None:
    assert _MIGRATION_0003.is_file(), f"missing {_MIGRATION_0003}"
    sql = _MIGRATION_0003.read_text(encoding="utf-8")
    assert re.search(r"DROP\s+TABLE\s+IF\s+EXISTS\s+app\.enrollments", sql, re.IGNORECASE), sql
    assert re.search(
        r"INSERT\s+INTO\s+app\.schema_migrations.*'0003'",
        sql,
        re.IGNORECASE | re.DOTALL,
    ), sql


def test_fk_edges_exclude_enrollments() -> None:
    child_tables = {edge.child_table for edge in DSQL_FOREIGN_KEY_EDGES}
    assert "enrollments" not in child_tables
    labels = [edge.label for edge in DSQL_FOREIGN_KEY_EDGES]
    assert not any("enrollments" in label for label in labels)
