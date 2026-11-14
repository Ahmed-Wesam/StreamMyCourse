"""Contract: cfn-lint covers payments and other deployed stacks."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_cfn_lint_scripts_include_payments_stack() -> None:
    root = _repo_root()
    for script_name in ("cfn-lint-templates.sh", "cfn-lint-templates.ps1"):
        path = root / "scripts" / script_name
        text = path.read_text(encoding="utf-8")
        assert "payments-stack.yaml" in text
        assert "video-provider-edge-stack.yaml" in text
        assert "rds-stack.yaml" not in text
