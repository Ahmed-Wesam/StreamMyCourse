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

from sync_config import _parse_db_port, load_sync_config  # noqa: E402


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", 5432),
        ("   ", 5432),
        ("5432", 5432),
        ("  15432 ", 15432),
        ("nope", 5432),
    ],
)
def test_parse_db_port(raw: str, expected: int) -> None:
    assert _parse_db_port(raw) == expected


def test_load_sync_config_strips_env_and_defaults(monkeypatch) -> None:
    monkeypatch.setenv("DB_SECRET_ARN", " arn:x ")
    monkeypatch.setenv("DB_HOST", " db.local ")
    monkeypatch.setenv("DB_NAME", "   ")
    monkeypatch.setenv("DB_PORT", "15432")

    cfg = load_sync_config()
    assert cfg.db_secret_arn == "arn:x"
    assert cfg.db_host == "db.local"
    # blank -> default postgres
    assert cfg.db_name == "postgres"
    assert cfg.db_port == 15432

