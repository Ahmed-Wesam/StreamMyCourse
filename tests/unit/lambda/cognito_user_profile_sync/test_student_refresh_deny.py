"""Failing stub (Slice 0): student refresh deny via client_metadata_session_id vs RDS.

Mechanism under test: ``client_metadata_session_id_vs_rds_active_raise``
(See plans/student-single-session-refresh-spike.md)

Slice 2 must implement ``deny_stale_student_refresh`` and wire it from
``handle_pre_token_generation`` for ``TokenGeneration_RefreshTokens`` on the
student app client.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch

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

from sync_config import SyncConfig  # noqa: E402

# Slice 2: implement in session_sync.py (or handler.py) and export for tests.
from session_sync import (  # noqa: E402
    StudentSessionSupersededError,
    deny_stale_student_refresh,
    handle_pre_token_generation,
)

STUDENT_CLIENT_ID = "student-client-id-example"
TEACHER_CLIENT_ID = "teacher-client-id-example"


def _student_refresh_event(
    *,
    presented_session_id: str,
    active_session_id: str,
) -> Dict[str, Any]:
    return {
        "version": "1",
        "triggerSource": "TokenGeneration_RefreshTokens",
        "region": "eu-west-1",
        "userPoolId": "eu-west-1_example",
        "userName": "Google_123",
        "callerContext": {
            "awsSdkVersion": "aws-sdk-unknown-unknown",
            "clientId": STUDENT_CLIENT_ID,
        },
        "request": {
            "userAttributes": {
                "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "email": "student@example.com",
                "custom:active_session_id": active_session_id,
            },
            "groupConfiguration": {
                "groupsToOverride": [],
                "iamRolesToOverride": [],
                "preferredRole": None,
            },
            "clientMetadata": {
                "student_session_id": presented_session_id,
            },
        },
        "response": {},
    }


@pytest.fixture
def session_cfg() -> SyncConfig:
    return SyncConfig(
        db_secret_arn="arn:aws:secretsmanager:eu-west-1:123:secret:x",
        db_host="db.local",
        db_name="app",
        db_port=5432,
        student_client_id=STUDENT_CLIENT_ID,
        teacher_client_id=TEACHER_CLIENT_ID,
    )


def test_pre_token_refresh_denies_when_client_metadata_session_id_stale_vs_rds_active(
    session_cfg: SyncConfig,
) -> None:
    """Stale device presents S1; RDS active session is S2 → refresh must fail."""
    stale_session = "11111111-1111-1111-1111-111111111111"
    active_session = "22222222-2222-2222-2222-222222222222"
    evt = _student_refresh_event(
        presented_session_id=stale_session,
        active_session_id=active_session,
    )

    with patch(
        "session_sync.get_student_active_session_id",
        return_value=active_session,
    ):
        with pytest.raises(StudentSessionSupersededError):
            handle_pre_token_generation(evt, session_cfg)


def test_pre_token_refresh_allows_when_client_metadata_session_id_matches_rds_active(
    session_cfg: SyncConfig,
) -> None:
    """Active device presents same session as RDS → refresh proceeds with claim."""
    active_session = "22222222-2222-2222-2222-222222222222"
    evt = _student_refresh_event(
        presented_session_id=active_session,
        active_session_id=active_session,
    )

    with patch(
        "session_sync.get_student_active_session_id",
        return_value=active_session,
    ):
        out = handle_pre_token_generation(evt, session_cfg)

    claims = out["response"]["claimsOverrideDetails"]["claimsToAddOrOverride"]
    assert claims["student_session_id"] == active_session


def test_pre_token_refresh_denies_when_client_metadata_session_id_empty_and_rds_active(
    session_cfg: SyncConfig,
) -> None:
    """Option C: refresh without student_session_id metadata must fail when RDS has an active id."""
    active_session = "22222222-2222-2222-2222-222222222222"
    evt = _student_refresh_event(
        presented_session_id="",
        active_session_id=active_session,
    )

    with patch(
        "session_sync.get_student_active_session_id",
        return_value=active_session,
    ):
        with pytest.raises(StudentSessionSupersededError):
            handle_pre_token_generation(evt, session_cfg)


def test_pre_token_authentication_bumps_rds_without_cognito_mirror(session_cfg: SyncConfig) -> None:
    """Student login bump must not call Cognito AdminUpdateUserAttributes (Pre Token deadlock)."""
    evt: Dict[str, Any] = {
        "version": "1",
        "triggerSource": "TokenGeneration_Authentication",
        "region": "eu-west-1",
        "userPoolId": "eu-west-1_example",
        "userName": "Google_123",
        "callerContext": {"clientId": STUDENT_CLIENT_ID},
        "request": {
            "userAttributes": {
                "sub": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "email": "student@example.com",
            },
        },
        "response": {},
    }
    mock_factory = MagicMock()
    with (
        patch("session_sync.get_cached_connection_factory", return_value=mock_factory),
        patch("session_sync.set_student_active_session_id") as mock_set,
        patch("repo.mirror_student_active_session_attribute") as mock_mirror,
    ):
        out = handle_pre_token_generation(evt, session_cfg)

    mock_set.assert_called_once()
    mock_mirror.assert_not_called()
    session_id = out["response"]["claimsOverrideDetails"]["claimsToAddOrOverride"][
        "student_session_id"
    ]
    assert session_id == mock_set.call_args.kwargs["session_id"]


def test_deny_stale_student_refresh_raises_client_metadata_session_id_vs_rds_active() -> None:
    """Unit-level guard for the compare primitive used by the refresh deny path."""
    with pytest.raises(StudentSessionSupersededError):
        deny_stale_student_refresh(
            presented_session_id="11111111-1111-1111-1111-111111111111",
            active_session_id="22222222-2222-2222-2222-222222222222",
        )
