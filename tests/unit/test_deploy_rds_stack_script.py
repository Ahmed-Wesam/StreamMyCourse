"""Guard: deploy-rds-stack.sh must stay valid bash (local + CI parity for RDS packaging)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_deploy_rds_stack_script_passes_bash_syntax_check() -> None:
    root = _repo_root()
    script = root / "scripts" / "deploy-rds-stack.sh"
    assert script.is_file(), f"missing {script}"
    subprocess.run(
        ["bash", "-n", str(script)],
        check=True,
        cwd=str(root),
    )


def test_deploy_rds_stack_sh_honors_restore_db_snapshot_identifier() -> None:
    text = (_repo_root() / "scripts" / "deploy-rds-stack.sh").read_text(encoding="utf-8")
    assert "RESTORE_DB_SNAPSHOT_IDENTIFIER" in text
    assert "DbSnapshotIdentifier=${RESTORE_DB_SNAPSHOT_IDENTIFIER}" in text


def test_deploy_rds_stack_sh_preserves_db_snapshot_identifier_on_update() -> None:
    text = (_repo_root() / "scripts" / "deploy-rds-stack.sh").read_text(encoding="utf-8")
    assert "Preserving DbSnapshotIdentifier=" in text
    assert "ParameterKey=='DbSnapshotIdentifier'" in text
