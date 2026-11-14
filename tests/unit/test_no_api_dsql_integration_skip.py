"""Integration tree must not reference the removed preview Api-dsql stack."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INTEGRATION_ROOT = _REPO_ROOT / "tests" / "integration"
_FORBIDDEN = "Api-dsql"


def _integration_python_files() -> list[Path]:
    return sorted(_INTEGRATION_ROOT.rglob("*.py"))


@pytest.mark.parametrize(
    "relative_path",
    [p.relative_to(_REPO_ROOT).as_posix() for p in _integration_python_files()],
)
def test_integration_file_has_no_api_dsql_reference(relative_path: str) -> None:
    path = _REPO_ROOT / relative_path
    text = path.read_text(encoding="utf-8")
    assert _FORBIDDEN not in text, (
        f"{relative_path} still contains {_FORBIDDEN!r} — use prod stack helpers only"
    )