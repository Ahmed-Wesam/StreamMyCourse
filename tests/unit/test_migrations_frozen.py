"""DSQL-0 A1 — migration directory freeze contract."""

from __future__ import annotations

import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from check_migrations_frozen import ALLOWLIST, unexpected_migration_files

_MIGRATION_PATH_RE = re.compile(
    r"infrastructure/database/migrations/([0-9]{3}_[\w]+\.sql)"
)


def _cited_migration_basenames(*relative_paths: str) -> set[str]:
    cited: set[str] = set()
    for rel in relative_paths:
        text = (_REPO_ROOT / rel).read_text(encoding="utf-8")
        cited.update(_MIGRATION_PATH_RE.findall(text))
    return cited


def test_repo_migrations_match_frozen_allowlist() -> None:
    assert unexpected_migration_files(_REPO_ROOT) == []


def test_synthetic_extra_migration_is_unexpected(tmp_path: Path) -> None:
    mig = tmp_path / "infrastructure" / "database" / "migrations"
    mig.mkdir(parents=True)
    for name in sorted(ALLOWLIST):
        (mig / name).write_text("-- frozen stub\n", encoding="utf-8")
    (mig / "026_not_allowed.sql").write_text("-- synthetic extra\n", encoding="utf-8")
    assert unexpected_migration_files(tmp_path) == ["026_not_allowed.sql"]


def test_deploy_scripts_only_cite_allowlisted_migrations() -> None:
    cited = _cited_migration_basenames(
        "scripts/deploy-rds-stack.sh",
        ".github/workflows/deploy-backend.yml",
    )
    assert cited, "expected at least one migration path in deploy scripts"
    not_allowed = cited - ALLOWLIST
    assert not_allowed == set()


def test_allowlist_count_is_24() -> None:
    assert len(ALLOWLIST) == 24
