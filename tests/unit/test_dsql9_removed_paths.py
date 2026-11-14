"""DSQL-9 S3: RDS-only lambdas, migrations tree, seed, and related CI must be gone."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _assert_path_removed(root: Path, relative: str) -> None:
    path = root / relative
    assert not path.exists(), f"expected removed: {relative}"


def test_dsql9_removed_directories() -> None:
    root = _repo_root()
    for rel in (
        "infrastructure/lambda/rds_schema_apply",
        "infrastructure/lambda/rds_query",
        "infrastructure/database/migrations",
        "scripts/rs16-seed",
    ):
        _assert_path_removed(root, rel)


def test_dsql9_removed_scripts() -> None:
    _assert_path_removed(_repo_root(), "scripts/check_migrations_frozen.py")


def test_dsql9_ci_omits_frozen_migration_check() -> None:
    ci = (_repo_root() / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "check_migrations_frozen.py" not in ci


def test_dsql9_lambda_boundaries_omit_subscription_repo_allowlist() -> None:
    boundaries = (_repo_root() / "scripts" / "check_lambda_boundaries.py").read_text(
        encoding="utf-8"
    )
    assert "services/subscription/repo.py" not in boundaries
