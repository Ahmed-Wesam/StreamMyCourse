"""DSQL-5 S6 / D9: checkout precheck via direct Catalog-dsql invoke (preview only)."""

from __future__ import annotations

import os
import secrets
import string
import threading
import uuid
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.cognito_auth import (
    admin_delete_cognito_user,
    mint_native_signup_tokens,
    resolve_student_pool_config_or_skip,
)
from helpers.dsql_billing_integration import (
    count_pending_bundle_checkouts,
    delete_purchases_for_user,
    invoke_billing_checkout,
    invoke_billing_rollback_checkout,
)
from helpers.dsql_preview_access import delete_purchase_by_id, insert_paid_bundle_purchase

_REPO_SKIP = "checkout precheck integration runs only on StreamMyCourse-Api-dsql"


def _is_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip().endswith("Api-dsql")


pytestmark = pytest.mark.skipif(not _is_preview_stack(), reason=_REPO_SKIP)


def _email() -> str:
    return f"chk-precheck-{uuid.uuid4().hex[:12]}@researchspectrum.org"


def _password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return f"Rs6!{''.join(secrets.choice(alphabet) for _ in range(20))}aA1"


@pytest.fixture(scope="session")
def api_base_url() -> str:
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set")
    return value.rstrip("/")


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        yield client


def _ensure_user(api: ApiClient, pool) -> tuple[str, str, str]:
    email = _email()
    password = _password()
    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    headers = {"Authorization": f"Bearer {tokens.id_token}"}
    me = api.get_users_me(headers=headers)
    assert me.status_code == 200, me.text
    user_sub = str(me.json().get("userId") or me.json().get("cognitoSub") or "")
    assert user_sub
    return user_sub, email, password


def test_checkout_precheck_already_owned_inserts_no_pending(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    user_sub, email, _password = _ensure_user(api, pool)
    paid_id = ""
    try:
        paid_id = insert_paid_bundle_purchase(user_sub)
        out = invoke_billing_checkout(user_sub, product_type="bundle")
        assert out.get("blockReason") == "already_owned"
        assert count_pending_bundle_checkouts(user_sub) == 0
    finally:
        if paid_id:
            delete_purchase_by_id(paid_id)
        delete_purchases_for_user(user_sub)
        admin_delete_cognito_user(cfg=pool, username=email)


def test_checkout_precheck_sequential_second_call_in_progress(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    user_sub, email, _password = _ensure_user(api, pool)
    created_ids: list[str] = []
    try:
        first = invoke_billing_checkout(user_sub, product_type="bundle")
        assert first.get("blockReason") is None, first
        pid = str((first.get("product") or {}).get("purchase_id") or "")
        assert pid
        created_ids.append(pid)
        second = invoke_billing_checkout(user_sub, product_type="bundle")
        assert second.get("blockReason") == "checkout_in_progress"
        assert count_pending_bundle_checkouts(user_sub) == 1
    finally:
        invoke_billing_rollback_checkout(user_sub, product_type="bundle")
        for pid in created_ids:
            delete_purchase_by_id(pid)
        delete_purchases_for_user(user_sub)
        admin_delete_cognito_user(cfg=pool, username=email)


def test_checkout_precheck_concurrent_reserve_one_pending_row(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    user_sub, email, _password = _ensure_user(api, pool)
    results: list[dict] = []
    errors: list[str] = []
    created_ids: list[str] = []

    def worker() -> None:
        try:
            results.append(invoke_billing_checkout(user_sub, product_type="bundle"))
        except Exception as exc:
            errors.append(str(exc))

    try:
        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join(timeout=60.0)
        t2.join(timeout=60.0)
        assert not errors, errors
        assert len(results) == 2

        reasons = [r.get("blockReason") for r in results]
        assert reasons.count(None) == 1
        assert reasons.count("checkout_in_progress") == 1

        winner = next(r for r in results if r.get("blockReason") is None)
        pid = str((winner.get("product") or {}).get("purchase_id") or "")
        assert pid
        created_ids.append(pid)
        assert count_pending_bundle_checkouts(user_sub) == 1
    finally:
        invoke_billing_rollback_checkout(user_sub, product_type="bundle")
        for pid in created_ids:
            delete_purchase_by_id(pid)
        delete_purchases_for_user(user_sub)
        admin_delete_cognito_user(cfg=pool, username=email)
