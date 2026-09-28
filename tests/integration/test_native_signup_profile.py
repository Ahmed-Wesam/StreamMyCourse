"""RS-6: disposable native sign-up + PATCH /users/me against deployed prod stacks.

Requires AWS credentials (auth stack describe + Cognito admin APIs) and
INTEGRATION_API_BASE_URL. Skips when the student client lacks native SRP/COGNITO
or PATCH /users/me is not deployed (migration 016 / API stage).
"""

from __future__ import annotations

import os
import secrets
import string
import uuid
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.cognito_auth import (
    admin_delete_cognito_user,
    mint_native_signup_tokens,
    resolve_student_pool_config_or_skip,
    student_client_supports_native_signup,
)

_TERMS_AT = "2026-09-27T10:00:00Z"
_PRIVACY_AT = "2026-09-27T10:00:01Z"


def _rs6_test_email() -> str:
    return f"rs6-test-{uuid.uuid4().hex[:12]}@researchspectrum.org"


def _strong_password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    core = "".join(secrets.choice(alphabet) for _ in range(20))
    return f"Rs6!{core}aA1"


def _valid_patch_body() -> dict[str, str]:
    return {
        "givenName": "RS",
        "familyName": "Integration",
        "country": "Jordan",
        "profession": "Researcher",
        "institution": "RS Institute",
        "researchInterests": "Statistics",
        "termsAcceptedAt": _TERMS_AT,
        "privacyAcceptedAt": _PRIVACY_AT,
    }


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set — see tests/integration/README.md")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


def test_native_signup_patch_and_get_users_me_profile(api: ApiClient) -> None:
    """Sign up via Cognito, PATCH profile fields, GET /users/me reflects RDS row."""
    pool = resolve_student_pool_config_or_skip()
    if not student_client_supports_native_signup(pool):
        pytest.skip(
            "Student app client missing ALLOW_USER_SRP_AUTH, ALLOW_ADMIN_USER_PASSWORD_AUTH, "
            "or COGNITO identity provider (RS-6 auth stack not deployed)"
        )

    email = _rs6_test_email()
    password = _strong_password()
    try:
        tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
        headers = {"Authorization": f"Bearer {tokens.id_token}"}

        patch_resp = api.patch_users_me(body=_valid_patch_body(), headers=headers)
        if patch_resp.status_code == 404:
            pytest.skip(
                "PATCH /users/me returned 404 — migration 016 or API Gateway method "
                "may not be deployed on this stage"
            )
        assert patch_resp.status_code == 200, patch_resp.text

        get_resp = api.get_users_me(headers=headers)
        assert get_resp.status_code == 200, get_resp.text
        data = get_resp.json()
        assert data.get("country") == "Jordan"
        assert data.get("profession") == "Researcher"
        assert data.get("termsAcceptedAt") == _TERMS_AT
        assert data.get("privacyAcceptedAt") == _PRIVACY_AT
        assert data.get("givenName") == "RS"
        assert data.get("familyName") == "Integration"
    finally:
        admin_delete_cognito_user(cfg=pool, username=email)
