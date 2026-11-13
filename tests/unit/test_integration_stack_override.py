"""DSQL-1 S5 — integration runners honor INTEGRATION_API_STACK with prod default."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_bash_runner_honors_integration_api_stack() -> None:
    text = (_repo_root() / "scripts" / "run-local-integration-tests.sh").read_text(
        encoding="utf-8"
    )
    assert "INTEGRATION_API_STACK" in text
    assert 'API_STACK="${INTEGRATION_API_STACK:-StreamMyCourse-Api-prod}"' in text


def test_powershell_runner_honors_integration_api_stack() -> None:
    text = (_repo_root() / "scripts" / "run-integration-tests.ps1").read_text(
        encoding="utf-8"
    )
    assert "INTEGRATION_API_STACK" in text
    assert "StreamMyCourse-Api-prod" in text
    assert (
        "$env:INTEGRATION_API_STACK" in text
        or '${env:INTEGRATION_API_STACK}' in text
    )
