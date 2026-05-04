"""Auth-related integration probes: `/users/me`, CORS, and Gateway vs Lambda auth modes.

Deployments without ``CognitoUserPoolArn`` on the API stack return **503** from
``GET /users/me`` (`auth_not_configured`) — Lambda sees ``COGNITO_AUTH_ENABLED=false``.

When Cognito authorizers are enabled, missing ``Authorization`` typically yields **401**
from API Gateway before the Lambda runs."""

from __future__ import annotations

import os

import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title


def test_users_me_contract_matches_auth_deployment(api: ApiClient) -> None:
    """503 = Lambda auth not enabled; 401 = JWT required at gateway; 200 = valid session."""
    resp = api.get_users_me()
    if resp.status_code == 503:
        body = resp.json()
        assert body.get("code") == "auth_not_configured"
        assert "cognito" in body.get("message", "").lower() or "authorizer" in body.get(
            "message", ""
        ).lower()
    elif resp.status_code == 401:
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


@pytest.mark.skipif(
    not os.environ.get("INTEG_COGNITO_JWT", "").strip(),
    reason="Set INTEG_COGNITO_JWT to an ID or access JWT for Cognito-backed environments.",
)
def test_users_me_with_bearer_returns_profile_when_enforced(api: ApiClient) -> None:
    token = os.environ["INTEG_COGNITO_JWT"].strip()
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
    """201 when POST /courses is open; 401 when Cognito protects that method."""
    title = make_test_title("auth-gateway-probe")
    resp = api.create_course(title=title, description="")
    assert resp.status_code in (201, 401), resp.text
    if resp.status_code == 201:
        cid = resp.json().get("id", "")
        assert cid
        del_resp = api.delete_course(cid)
        # Delete may stay open on older stacks; when Cognito protects DELETE, safety net still sweeps by title prefix.
        assert del_resp.status_code in (200, 401), del_resp.text
