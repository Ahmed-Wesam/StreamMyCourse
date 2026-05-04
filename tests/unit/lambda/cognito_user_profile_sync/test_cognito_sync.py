"""Unit tests for Cognito PostAuthentication user profile sync."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

_COGNITO_SRC = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "infrastructure", "lambda", "cognito_user_profile_sync")
)
if _COGNITO_SRC not in sys.path:
    sys.path.insert(0, _COGNITO_SRC)
from unittest.mock import MagicMock, patch

import pytest

from handler import sync_post_authentication
from sync_config import SyncConfig


def _sample_post_auth_event(
    *,
    sub: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    email: str = "student@example.com",
    role_attr: str | None = "teacher",
    use_custom_role_key: bool = True,
) -> Dict[str, Any]:
    attrs: Dict[str, str] = {
        "sub": sub,
        "email": email,
    }
    if role_attr is not None:
        key = "custom:role" if use_custom_role_key else "role"
        attrs[key] = role_attr
    return {
        "version": "1",
        "triggerSource": "PostAuthentication_Authentication",
        "region": "eu-west-1",
        "userPoolId": "eu-west-1_example",
        "userName": "Google_123",
        "request": {"userAttributes": attrs},
        "response": {},
    }


@pytest.fixture
def rds_cfg() -> SyncConfig:
    return SyncConfig(
        db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:x",
        db_host="db.local",
        db_name="app",
        db_port=5432,
    )


def test_sync_skips_without_sub(rds_cfg: SyncConfig) -> None:
    evt: Dict[str, Any] = _sample_post_auth_event()
    del evt["request"]["userAttributes"]["sub"]  # type: ignore[index]
    with patch("handler.upsert_user_profile") as mock_upsert:
        out = sync_post_authentication(evt, rds_cfg)
    assert out is evt
    mock_upsert.assert_not_called()


def test_sync_skips_when_db_not_configured() -> None:
    cfg = SyncConfig(db_secret_arn="", db_host="", db_name="app", db_port=5432)
    evt = _sample_post_auth_event()
    with patch("handler.upsert_user_profile") as mock_upsert:
        out = sync_post_authentication(evt, cfg)
    assert out is evt
    mock_upsert.assert_not_called()


def test_sync_calls_upsert_with_normalized_role(rds_cfg: SyncConfig) -> None:
    evt = _sample_post_auth_event(role_attr="Admin")
    mock_factory = MagicMock()
    with (
        patch("handler.get_cached_connection_factory", return_value=mock_factory),
        patch("handler.upsert_user_profile") as mock_upsert,
    ):
        sync_post_authentication(evt, rds_cfg)
    mock_upsert.assert_called_once()
    args, kwargs = mock_upsert.call_args
    assert args[0] is mock_factory
    assert kwargs["user_sub"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert kwargs["email"] == "student@example.com"
    assert kwargs["role"] == "admin"


def test_sync_uses_role_attr_when_custom_missing(rds_cfg: SyncConfig) -> None:
    evt = _sample_post_auth_event(role_attr="student", use_custom_role_key=False)
    mock_factory = MagicMock()
    with (
        patch("handler.get_cached_connection_factory", return_value=mock_factory),
        patch("handler.upsert_user_profile") as mock_upsert,
    ):
        sync_post_authentication(evt, rds_cfg)
    assert mock_upsert.call_args.kwargs["role"] == "student"


def test_sync_does_not_raise_on_upsert_failure(rds_cfg: SyncConfig) -> None:
    evt = _sample_post_auth_event()
    mock_factory = MagicMock()
    with (
        patch("handler.get_cached_connection_factory", return_value=mock_factory),
        patch("handler.upsert_user_profile", side_effect=RuntimeError("db down")),
    ):
        out = sync_post_authentication(evt, rds_cfg)
    assert out is evt


def test_lambda_handler_uses_config_loader() -> None:
    cfg = SyncConfig(
        db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:x",
        db_host="db.local",
        db_name="app",
        db_port=5432,
    )
    evt = _sample_post_auth_event()
    with (
        patch("handler._config_loader", return_value=cfg),
        patch("handler.sync_post_authentication", return_value={"ok": True}) as sync_mock,
    ):
        from handler import lambda_handler

        out = lambda_handler(evt, None)
    sync_mock.assert_called_once()
    assert out == {"ok": True}
