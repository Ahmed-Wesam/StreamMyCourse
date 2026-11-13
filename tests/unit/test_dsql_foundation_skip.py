"""Unit check: DSQL foundation integration module skips without Api-dsql stack."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_FOUNDATION = (
    Path(__file__).resolve().parents[1] / "integration" / "test_dsql_foundation.py"
)
_INTEGRATION = _FOUNDATION.parent


def _load_foundation_module():
    integration_path = str(_INTEGRATION)
    if integration_path not in sys.path:
        sys.path.insert(0, integration_path)
    spec = importlib.util.spec_from_file_location("test_dsql_foundation", _FOUNDATION)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_dsql_foundation_module_has_api_dsql_skip_marker() -> None:
    text = _FOUNDATION.read_text(encoding="utf-8")
    assert "pytest.mark.skipif" in text
    assert "Api-dsql" in text
    assert "courses.status" not in text
    assert "'deleting'" not in text

    mod = _load_foundation_module()
    is_dsql = mod._is_dsql_preview_stack
    prev = os.environ.get("INTEGRATION_API_STACK")
    try:
        os.environ.pop("INTEGRATION_API_STACK", None)
        assert not is_dsql()
        os.environ["INTEGRATION_API_STACK"] = "StreamMyCourse-Api-prod"
        assert not is_dsql()
        os.environ["INTEGRATION_API_STACK"] = "StreamMyCourse-Api-dsql"
        assert is_dsql()
    finally:
        if prev is None:
            os.environ.pop("INTEGRATION_API_STACK", None)
        else:
            os.environ["INTEGRATION_API_STACK"] = prev
