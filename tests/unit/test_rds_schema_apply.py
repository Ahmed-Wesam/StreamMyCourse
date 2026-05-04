"""Unit tests for the RDS schema-applier Lambda (SQL splitting only).

The handler lives under ``infrastructure/lambda/`` (outside the catalog package) so
we load it by path to avoid coupling the catalog test tree to that layout."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_INDEX = _ROOT / "infrastructure" / "lambda" / "rds_schema_apply" / "index.py"


@pytest.fixture(scope="module")
def schema_apply():
    spec = importlib.util.spec_from_file_location("rds_schema_apply_index", _INDEX)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_split_sql_strips_full_line_comments(schema_apply):
    sql = """-- leading
CREATE TABLE IF NOT EXISTS a (id INT);
-- between
CREATE TABLE IF NOT EXISTS b (id INT);
"""
    parts = schema_apply._split_sql_statements(sql)
    assert len(parts) == 2
    assert "CREATE TABLE IF NOT EXISTS a" in parts[0]
    assert "CREATE TABLE IF NOT EXISTS b" in parts[1]


def test_split_sql_empty_and_whitespace(schema_apply):
    assert schema_apply._split_sql_statements("") == []
    assert schema_apply._split_sql_statements("   \n  -- only comment\n") == []


def test_split_real_migration_file_contains_expected_ddl(schema_apply):
    path = _ROOT / "infrastructure" / "database" / "migrations" / "001_initial_schema.sql"
    sql = path.read_text(encoding="utf-8")
    parts = schema_apply._split_sql_statements(sql)
    joined = "\n".join(parts)
    assert "CREATE EXTENSION IF NOT EXISTS" in joined
    assert "CREATE TABLE IF NOT EXISTS users" in joined
    assert "CREATE TABLE IF NOT EXISTS courses" in joined
    assert "CREATE TABLE IF NOT EXISTS lessons" in joined
    assert "CREATE TABLE IF NOT EXISTS enrollments" in joined
    assert len(parts) >= 8
