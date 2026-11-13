"""DSQL-2 S6: operator delete-user against preview DSQL + Cognito."""

from __future__ import annotations

import importlib.util
import os
import secrets
import string
import sys
import uuid
from pathlib import Path
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.cognito_auth import mint_native_signup_tokens, resolve_student_pool_config_or_skip
from helpers.dsql_audit import admin_connect

_REPO = Path(__file__).resolve().parents[2]


def _is_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip().endswith("Api-dsql")


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _is_preview_stack(),
        reason="user deletion integration runs only on StreamMyCourse-Api-dsql",
    ),
]


def _email() -> str:
    return f"del-test-{uuid.uuid4().hex[:12]}@researchspectrum.org"


def _password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return f"Rs6!{''.join(secrets.choice(alphabet) for _ in range(20))}aA1"


def _load_delete_user():
    path = _REPO / "scripts" / "delete-user.py"
    spec = importlib.util.spec_from_file_location("delete_user_int", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    catalog = _REPO / "infrastructure" / "lambda" / "catalog"
    if str(catalog) not in sys.path:
        sys.path.insert(0, str(catalog))
    spec.loader.exec_module(mod)
    return mod


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


def test_operator_delete_user_removes_dsql_row_and_cognito(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    email = _email()
    password = _password()
    mod = _load_delete_user()
    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    headers = {"Authorization": f"Bearer {tokens.id_token}"}
    me = api.get_users_me(headers=headers)
    assert me.status_code == 200, me.text
    user_sub = me.json().get("userSub") or ""
    assert user_sub

    rc = mod.run(
        ["--user-sub", user_sub, "--execute"],
        cognito=mod._BotoCognito(),
        service_factory=mod._build_service,
        endpoint_resolver=mod._resolve_dsql_endpoint,
        pool_resolver=mod._resolve_user_pool_id,
    )
    assert rc == 0, "delete-user.py should exit 0"

    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users WHERE user_sub = %s", (user_sub,))
            row = cur.fetchone()
            assert row is not None and int(row[0]) == 0

    import boto3
    from botocore.exceptions import ClientError

    client = boto3.client("cognito-idp")
    with pytest.raises(ClientError) as exc:
        client.admin_get_user(UserPoolId=pool.user_pool_id, Username=email)
    assert exc.value.response["Error"]["Code"] == "UserNotFoundException"
