"""Student single-session integration tests (Slice 5).

Exercises deployed catalog + Cognito Pre Token session bump/deny:
1. Mint JWT1 (student client) → GET /users/me 200
2. Mint JWT2 (same user) → bumps active session
3. GET /users/me with JWT1 → 401 session_superseded
4. Refresh JWT1 refresh token with stale student_session_id metadata → denied
5. Teacher JWT unaffected (optional)
"""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.cognito_auth import (
    mint_student_password_auth,
    resolve_student_cognito_config_or_skip,
    try_refresh_student_tokens_with_metadata,
)

SESSION_SUPERSEDED = "session_superseded"


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set — see tests/integration/README.md")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    """Anonymous client; bearer tokens are supplied per request in these tests."""
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


def _bearer(id_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {id_token}"}


def _assert_users_me_ok(api: ApiClient, id_token: str) -> None:
    resp = api.get_users_me(headers=_bearer(id_token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data.get("userId")
    assert data.get("role") in ("student", "teacher", "admin")


def _assert_session_superseded(api: ApiClient, id_token: str) -> None:
    resp = api.get_users_me(headers=_bearer(id_token))
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body.get("code") == SESSION_SUPERSEDED, body


def test_student_single_session_superseded_and_refresh_denied(api: ApiClient) -> None:
    """Second student login invalidates the first IdToken and blocks stale refresh."""
    cfg = resolve_student_cognito_config_or_skip()

    tokens1 = mint_student_password_auth(cfg)
    _assert_users_me_ok(api, tokens1.id_token)

    if not tokens1.student_session_id:
        pytest.skip(
            "student_session_id claim missing on first IdToken — "
            "single-session Pre Token Generation may not be deployed"
        )

    tokens2 = mint_student_password_auth(cfg)
    assert tokens2.student_session_id
    assert tokens2.student_session_id != tokens1.student_session_id, (
        "Second student auth should allocate a new session id"
    )

    _assert_session_superseded(api, tokens1.id_token)

    refreshed = try_refresh_student_tokens_with_metadata(
        cfg=cfg,
        refresh_token=tokens1.refresh_token,
        student_session_id=tokens1.student_session_id,
    )
    assert refreshed is None, "Stale refresh must not return a usable IdToken"


def test_teacher_jwt_unaffected_by_student_single_session(api: ApiClient) -> None:
    """Teacher principal is not subject to student session compare."""
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT not set (teacher principal)")

    me_resp = api.get_users_me(headers=_bearer(token))
    assert me_resp.status_code == 200, me_resp.text

    mine_resp = api.list_my_courses(headers=_bearer(token))
    assert mine_resp.status_code == 200, mine_resp.text
