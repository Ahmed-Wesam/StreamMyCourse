"""Guard: deploy-edge.sh must stay valid bash (used by Deploy workflow)."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_deploy_edge_script_passes_bash_syntax_check() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "deploy-edge.sh"
    assert script.is_file(), f"missing {script}"
    subprocess.run(
        ["bash", "-n", str(script)],
        check=True,
        cwd=str(root),
    )


def test_deploy_edge_uses_single_us_east1_edge_hosting_stack() -> None:
    """Unified edge: one CFN stack in us-east-1 (cert + both SPAs), not three stacks."""
    root = Path(__file__).resolve().parents[2]
    text = (root / "scripts" / "deploy-edge.sh").read_text(encoding="utf-8")
    assert "StreamMyCourse-EdgeHosting-" in text
    assert "edge-hosting-stack.yaml" in text
    assert "web-cert-stack.yaml" not in text
    assert "web-stack.yaml" not in text
    assert "teacher-web-stack.yaml" not in text
    deploy_lines = [ln for ln in text.splitlines() if "cloudformation deploy" in ln]
    assert len(deploy_lines) == 1, f"expected exactly one deploy, got {deploy_lines!r}"
    assert "us-east-1" in text
    assert "StreamMyCourse-Cert-" not in text
    assert "StreamMyCourse-Web-" not in text
    assert "StreamMyCourse-TeacherWeb-" not in text
    assert "AttachCloudFrontAliases=" in text
    assert "EDGE_ATTACH_CF_ALIASES" in text
