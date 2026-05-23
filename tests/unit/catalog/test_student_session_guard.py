"""Slice 3: catalog API middleware for student single-session enforcement."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

from services.auth.session import SESSION_SUPERSEDED, check_student_session

STUDENT_CLIENT_ID = "student-client-id-example"
TEACHER_CLIENT_ID = "teacher-client-id-example"
USER_SUB = "11111111-1111-1111-1111-111111111111"
ACTIVE_SESSION = "22222222-2222-2222-2222-222222222222"
OTHER_SESSION = "33333333-3333-3333-3333-333333333333"
ORIGIN = "https://student.example.com"


def _event(
    *,
    aud: str = STUDENT_CLIENT_ID,
    sub: str = USER_SUB,
    student_session_id: Optional[str] = ACTIVE_SESSION,
) -> Dict[str, Any]:
    claims: Dict[str, Any] = {"aud": aud, "sub": sub}
    if student_session_id is not None:
        claims["student_session_id"] = student_session_id
    return {
        "requestContext": {
            "authorizer": {
                "claims": claims,
            },
        },
    }


class TestCheckStudentSession:
    def test_skips_when_student_client_id_unconfigured(self) -> None:
        repo = MagicMock()
        assert (
            check_student_session(_event(), ORIGIN, repo, "")
            is None
        )
        repo.get_student_active_session_id.assert_not_called()

    def test_skips_teacher_audience(self) -> None:
        repo = MagicMock()
        assert (
            check_student_session(
                _event(aud=TEACHER_CLIENT_ID, student_session_id=OTHER_SESSION),
                ORIGIN,
                repo,
                STUDENT_CLIENT_ID,
            )
            is None
        )
        repo.get_student_active_session_id.assert_not_called()

    def test_skips_when_sub_missing(self) -> None:
        repo = MagicMock()
        assert (
            check_student_session(
                _event(sub=""),
                ORIGIN,
                repo,
                STUDENT_CLIENT_ID,
            )
            is None
        )
        repo.get_student_active_session_id.assert_not_called()

    def test_allows_matching_student_session(self) -> None:
        repo = MagicMock()
        repo.get_student_active_session_id.return_value = ACTIVE_SESSION

        assert (
            check_student_session(_event(), ORIGIN, repo, STUDENT_CLIENT_ID)
            is None
        )
        repo.get_student_active_session_id.assert_called_once_with(USER_SUB)

    def test_allows_when_rds_active_session_empty(self) -> None:
        repo = MagicMock()
        repo.get_student_active_session_id.return_value = ""

        assert (
            check_student_session(
                _event(student_session_id=OTHER_SESSION),
                ORIGIN,
                repo,
                STUDENT_CLIENT_ID,
            )
            is None
        )

    @pytest.mark.parametrize("presented", [OTHER_SESSION, None, ""])
    def test_rejects_superseded_student_session(
        self, presented: str | None
    ) -> None:
        repo = MagicMock()
        repo.get_student_active_session_id.return_value = ACTIVE_SESSION
        event = _event()
        if presented is None:
            event["requestContext"]["authorizer"]["claims"].pop(
                "student_session_id", None
            )
        else:
            event["requestContext"]["authorizer"]["claims"][
                "student_session_id"
            ] = presented

        response = check_student_session(
            event, ORIGIN, repo, STUDENT_CLIENT_ID
        )

        assert response is not None
        assert response["statusCode"] == 401
        body = json.loads(response["body"])
        assert body == {
            "message": "Your account was signed in elsewhere.",
            "code": SESSION_SUPERSEDED,
        }
        assert response["headers"]["Access-Control-Allow-Origin"] == ORIGIN
