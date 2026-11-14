"""DSQL-9 S4: persistence smoke module replaces test_rds_path."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_dsql9_persistence_smoke_module_paths() -> None:
    root = _repo_root()
    assert not (root / "tests" / "integration" / "test_rds_path.py").exists()
    assert (root / "tests" / "integration" / "test_persistence_smoke.py").is_file()


def test_dsql9_persistence_smoke_module_source() -> None:
    src = (
        _repo_root() / "tests" / "integration" / "test_persistence_smoke.py"
    ).read_text(encoding="utf-8")
    assert "001_initial_schema" not in src
    assert "RDS" not in src


def test_dsql9_conftest_persistence_smoke_exemption() -> None:
    text = (_repo_root() / "tests" / "integration" / "conftest.py").read_text(
        encoding="utf-8"
    )
    assert "test_rds_path" not in text
    assert "test_persistence_smoke" in text
    assert "_run_is_persistence_smoke_only" in text
