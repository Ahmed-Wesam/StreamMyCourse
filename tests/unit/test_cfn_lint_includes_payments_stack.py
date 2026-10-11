"""Contract: cfn-lint covers the video edge stack and not the removed payments stack."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_cfn_lint_scripts_omit_removed_payments_stack() -> None:
    root = _repo_root()
    for script_name in ("cfn-lint-templates.sh", "cfn-lint-templates.ps1"):
        path = root / "scripts" / script_name
        text = path.read_text(encoding="utf-8")
        assert "payments-stack.yaml" not in text
        assert "video-provider-edge-stack.yaml" in text
