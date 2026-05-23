"""Student single-session compare rules (pure; no I/O).

Used by API middleware (Slice 2+) and mirrored in Cognito pre-token refresh (Slice 2).
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from services.auth.ports import UserProfileRepositoryPort
from services.common.http import apigw_cognito_claims, json_response

SESSION_SUPERSEDED = "session_superseded"


def evaluate_student_session(
    claims: Mapping[str, Any],
    active_session_id: str,
    student_client_id: str,
) -> Optional[str]:
    """Return ``None`` when the token is allowed; otherwise an error code string.

  Only tokens whose ``aud`` matches ``student_client_id`` are checked. Other
  audiences (e.g. teacher app client) are allowed without inspecting session claims.
  """
    if claims.get("aud") != student_client_id:
        return None

    active = (active_session_id or "").strip()
    if not active:
        return None

    presented = (
        claims.get("student_session_id") or claims.get("custom:student_session_id") or ""
    ).strip()
    if presented == active:
        return None

    return SESSION_SUPERSEDED


def check_student_session(
    event: Dict[str, Any],
    origin: Optional[str],
    repo: UserProfileRepositoryPort,
    student_client_id: str,
) -> Optional[Dict[str, Any]]:
    """Return a 401 API Gateway response when the student session is superseded.

    Returns ``None`` when the request may proceed (non-student token, anonymous,
    unconfigured client id, or session still active).
    """
    client_id = (student_client_id or "").strip()
    if not client_id:
        return None

    claims = apigw_cognito_claims(event)
    if claims.get("aud") != client_id:
        return None

    user_sub = str(claims.get("sub") or "").strip()
    if not user_sub:
        return None

    active_session_id = repo.get_student_active_session_id(user_sub)
    if evaluate_student_session(claims, active_session_id, client_id) != SESSION_SUPERSEDED:
        return None

    return json_response(
        401,
        {
            "message": "Your account was signed in elsewhere.",
            "code": SESSION_SUPERSEDED,
        },
        origin,
    )
