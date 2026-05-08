"""Auth-related integration probes: `/users/me`, CORS, and Gateway vs Lambda auth modes.

The API stack now requires Cognito and protects all non-public routes at API Gateway.
Missing ``Authorization`` typically yields **401** from API Gateway before the Lambda runs."""

from __future__ import annotations

import os

import httpx
import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title


def test_users_me_contract_matches_auth_deployment(api: ApiClient) -> None:
    """401 = JWT required at gateway; 200 = valid session."""
    resp = api.get_users_me()
    if resp.status_code == 401:
        text = resp.text.lower()
        if "unauthorized" not in text:
            try:
                assert resp.json().get("message") == "Unauthorized"
            except Exception:
                pytest.fail(f"Expected 401 unauthorized body; got {resp.text!r}")
    elif resp.status_code == 200:
        data = resp.json()
        assert data.get("userId")
        assert data.get("cognitoSub") == data.get("userId")
        assert data.get("role") in ("student", "teacher", "admin")
    else:
        pytest.fail(f"Unexpected GET /users/me status {resp.status_code}: {resp.text}")


def test_users_me_with_bearer_returns_profile_when_enforced(api: ApiClient) -> None:
    """Test that /users/me returns profile when authenticated with a valid JWT.

    This test requires INTEGRATION_COGNITO_JWT to be set. If not set, the test
    will fail rather than skip, ensuring the auth flow is properly tested.
    """
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    if not token:
        pytest.fail(
            "INTEGRATION_COGNITO_JWT environment variable is required for this test. "
            "Set it to a valid Cognito ID or access token for Cognito-backed environments."
        )
    resp = api.get_users_me(headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "userId" in data and data["role"] in ("student", "teacher", "admin")


def test_users_me_options_preflight_returns_204_and_allow_headers(api: ApiClient) -> None:
    resp = api.options("/users/me", origin="https://app.example.com")
    assert resp.status_code == 204
    allow_headers = resp.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
    assert "content-type" in allow_headers


def test_post_courses_without_bearer_reflects_gateway_policy(api: ApiClient) -> None:
    """POST /courses is protected by Cognito at the gateway."""
    title = make_test_title("auth-gateway-probe")
    base = str(api.raw.base_url).rstrip("/")
    with httpx.Client(base_url=base, timeout=30.0) as anon:
        resp = anon.post("/courses", json={"title": title, "description": ""})
    assert resp.status_code == 401, resp.text
