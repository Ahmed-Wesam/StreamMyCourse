"""Contract: payments-stack.yaml is included in repo cfn-lint scripts."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_cfn_lint_scripts_include_payments_stack() -> None:
    root = _repo_root()
    needle = "payments-stack.yaml"
    for script_name in ("cfn-lint-templates.sh", "cfn-lint-templates.ps1"):
        path = root / "scripts" / script_name
        assert path.is_file(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert needle in text, f"{script_name} must lint {needle}"
