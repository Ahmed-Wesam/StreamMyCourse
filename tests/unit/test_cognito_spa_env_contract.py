"""Build-time contract: when Cognito pool + client are set, VITE_COGNITO_DOMAIN is required."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _run_checker(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    root = _root()
    script = root / "scripts" / "check-cognito-spa-env.mjs"
    base = {k: v for k, v in os.environ.items() if not k.startswith("VITE_")}
    merged = {**base, "COGNITO_SPA_ENV_NO_DOTENV": "1", **env}
    return subprocess.run(
        ["node", str(script)],
        cwd=str(root),
        env=merged,
        capture_output=True,
        text=True,
        check=False,
    )


def test_pool_and_client_without_domain_fails_with_diagnosable_message() -> None:
    result = _run_checker(
        {
            "VITE_COGNITO_USER_POOL_ID": "eu-west-1_testpool",
            "VITE_COGNITO_USER_POOL_CLIENT_ID": "abc123clientid456789012345",
        }
    )
    assert result.returncode == 1, (result.stdout, result.stderr)
    combined = f"{result.stdout}\n{result.stderr}"
    assert "VITE_COGNITO_DOMAIN" in combined


def test_all_three_vars_set_succeeds() -> None:
    result = _run_checker(
        {
            "VITE_COGNITO_USER_POOL_ID": "eu-west-1_testpool",
            "VITE_COGNITO_USER_POOL_CLIENT_ID": "abc123clientid456789012345",
            "VITE_COGNITO_DOMAIN": "prefix.auth.eu-west-1.amazoncognito.com",
        }
    )
    assert result.returncode == 0, (result.stdout, result.stderr)


def test_pool_unset_succeeds_even_if_client_set() -> None:
    result = _run_checker(
        {
            "VITE_COGNITO_USER_POOL_CLIENT_ID": "orphanclientid0123456789012",
        }
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
