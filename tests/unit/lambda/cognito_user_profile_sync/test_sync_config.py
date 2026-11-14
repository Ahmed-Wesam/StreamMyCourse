from __future__ import annotations

import os
import sys

import pytest

_COGNITO_SRC = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "..",
        "..",
        "infrastructure",
        "lambda",
        "cognito_user_profile_sync",
    )
)
if _COGNITO_SRC not in sys.path:
    sys.path.insert(0, _COGNITO_SRC)

from sync_config import load_sync_config  # noqa: E402


def test_load_sync_config_strips_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DSQL_ENDPOINT", " cluster.dsql.example ")
    monkeypatch.setenv("STUDENT_COGNITO_CLIENT_ID", " student-id ")
    monkeypatch.setenv("TEACHER_COGNITO_CLIENT_ID", " teacher-id ")

    cfg = load_sync_config()
    assert cfg.dsql_endpoint == "cluster.dsql.example"
    assert cfg.student_client_id == "student-id"
    assert cfg.teacher_client_id == "teacher-id"
