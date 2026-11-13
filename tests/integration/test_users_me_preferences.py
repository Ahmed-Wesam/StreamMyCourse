"""DSQL-2 S6: learning preference tags round-trip on prod (RDS) and preview (DSQL)."""

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

pytestmark = pytest.mark.integration


def _email() -> str:
    return f"pref-test-{uuid.uuid4().hex[:12]}@researchspectrum.org"


def _password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return f"Rs6!{''.join(secrets.choice(alphabet) for _ in range(20))}aA1"


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


def test_users_me_learning_preferences_round_trip(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    if not student_client_supports_native_signup(pool):
        pytest.skip("Student pool lacks native signup")

    email = _email()
    password = _password()
    try:
        tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
        headers = {"Authorization": f"Bearer {tokens.id_token}"}

        get0 = api.get_users_me(headers=headers)
        assert get0.status_code == 200, get0.text

        patch1 = api.patch_users_me(
            headers=headers,
            body={
                "autoplayNext": False,
                "autoMarkComplete": False,
                "progressCelebrations": False,
                "researchInterestTags": ["surgical_research"],
            },
        )
        assert patch1.status_code == 200, patch1.text
        body1 = patch1.json()
        assert body1.get("researchInterestTags") == ["surgical_research"]

        get1 = api.get_users_me(headers=headers)
        assert get1.status_code == 200
        assert get1.json().get("researchInterestTags") == ["surgical_research"]

        patch2 = api.patch_users_me(headers=headers, body={"resetPreferences": True})
        assert patch2.status_code == 200, patch2.text
        assert patch2.json().get("researchInterestTags") == [
            "systematic_reviews",
            "meta_analysis",
        ]

        get2 = api.get_users_me(headers=headers)
        assert get2.status_code == 200
        assert get2.json().get("researchInterestTags") == [
            "systematic_reviews",
            "meta_analysis",
        ]
    finally:
        admin_delete_cognito_user(cfg=pool, username=email)
