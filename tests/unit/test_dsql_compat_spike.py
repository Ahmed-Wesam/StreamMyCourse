"""DSQL-1 S2 — compatibility spike script contract (TDD Red → Green, no live DB)."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

SPIKE_SCHEMA = "spike"

# Critical SQL shapes from plans/dsql-ws1-foundation.md §9 (substring anchors).
CRITICAL_MARKERS: tuple[str, ...] = (
    "gen_random_uuid()",
    "ON DELETE CASCADE",
    "ON DELETE NO ACTION",
    "CREATE UNIQUE INDEX ASYNC",
    " WHERE ",
    "CALL sys.wait_for_job",
    "ON CONFLICT DO NOTHING",
    "CREATE INDEX ASYNC IF NOT EXISTS",
    "GRANT USAGE ON SCHEMA",
    "GRANT SELECT, INSERT, UPDATE, DELETE",
    "SET search_path TO app",
)

# smc_app probe SQL (second connection in live mode; listed for dry-run visibility).
SMC_APP_MARKERS: tuple[str, ...] = (
    "INSERT INTO",
    "DELETE FROM",
    "CREATE TABLE",
)

INFORMATIONAL_MARKERS: tuple[str, ...] = (
    "DISTINCT ON",
    "ANY(%s::uuid[])",
    "ANY(%s)",
    "make_interval(secs =>",
    "(NOW() AT TIME ZONE 'UTC') - (INTERVAL '1 minute' *",
    "JSONB",
)

DSN_LEAK_PATTERN = re.compile(
    r"(password|token|dsn|postgresql://|secret)",
    re.IGNORECASE,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _spike_script_path() -> Path:
    return _repo_root() / "scripts" / "dsql_compat_spike.py"


def _load_spike_module():
    path = _spike_script_path()
    assert path.is_file(), f"missing spike script {path}"
    spec = importlib.util.spec_from_file_location("dsql_compat_spike", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_spike_module_exports_statement_lists() -> None:
    mod = _load_spike_module()
    assert mod.SPIKE_SCHEMA == SPIKE_SCHEMA
    critical = mod.critical_sql_statements()
    informational = mod.informational_sql_statements()
    assert isinstance(critical, list) and critical, "critical_sql_statements must be non-empty"
    assert isinstance(informational, list) and informational, (
        "informational_sql_statements must be non-empty"
    )
    assert all(isinstance(s, str) and s.strip() for s in critical)
    assert all(isinstance(s, str) and s.strip() for s in informational)


def test_critical_statements_cover_section_nine() -> None:
    mod = _load_spike_module()
    joined = "\n".join(mod.critical_sql_statements()) + "\n".join(
        mod.smc_app_probe_sql_statements()
    )
    for marker in CRITICAL_MARKERS:
        assert marker in joined, f"critical spike SQL missing {marker!r}"
    for marker in SMC_APP_MARKERS:
        assert marker in joined, f"smc_app probe SQL missing {marker!r}"


def test_informational_statements_cover_section_nine() -> None:
    mod = _load_spike_module()
    joined = "\n".join(mod.informational_sql_statements())
    for marker in INFORMATIONAL_MARKERS:
        assert marker in joined, f"informational spike SQL missing {marker!r}"
    assert "ORDER BY" in joined and "DISTINCT ON" in joined
    assert "FOR UPDATE" not in joined, (
        "informational_sql_statements must not list FOR UPDATE (DSQL-6 D8)"
    )


def test_distinct_on_shape_matches_question_banks_repo() -> None:
    mod = _load_spike_module()
    distinct_sql = next(
        s for s in mod.informational_sql_statements() if "DISTINCT ON" in s
    )
    assert "module_id" in distinct_sql
    assert "submitted_at DESC" in distinct_sql


def test_connection_error_rewrite_host_only() -> None:
    mod = _load_spike_module()
    host = "abc123.dsql.eu-west-1.on.aws"
    secret_exc = RuntimeError(
        "could not connect: postgresql://admin:eyJhbGciOiJIUzI1NiJ9@abc123.dsql.eu-west-1.on.aws/postgres"
    )
    err = mod.connection_error(host, secret_exc)
    assert isinstance(err, RuntimeError)
    message = str(err)
    assert host in message
    assert "postgresql://" not in message
    assert "eyJ" not in message
    assert not DSN_LEAK_PATTERN.search(message)


def test_libpq_statement_timeout_option_documented() -> None:
    mod = _load_spike_module()
    opt = getattr(mod, "LIBPQ_STATEMENT_TIMEOUT_OPTIONS", None)
    assert isinstance(opt, str) and "statement_timeout" in opt


def test_dry_run_statement_order_is_deterministic() -> None:
    mod = _load_spike_module()
    lines = mod.dry_run_sql_lines()
    assert lines == mod.dry_run_sql_lines()
    assert lines[0].upper().startswith("DROP SCHEMA IF EXISTS")
    assert any(l.upper().startswith("CREATE SCHEMA") for l in lines)
    assert any("DROP SCHEMA" in line.upper() for line in lines)
