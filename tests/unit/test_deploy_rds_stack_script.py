"""Guard: deploy-rds-stack.sh must stay valid bash (local + CI parity for RDS packaging)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_deploy_rds_stack_script_passes_bash_syntax_check() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "deploy-rds-stack.sh"
    assert script.is_file(), f"missing {script}"
    subprocess.run(
        ["bash", "-n", str(script)],
        check=True,
        cwd=str(root),
    )
