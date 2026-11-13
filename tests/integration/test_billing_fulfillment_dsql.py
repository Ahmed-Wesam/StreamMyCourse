"""DSQL-5 S6 / D10: fulfillment repo against Aurora DSQL (no HyperPay HTTP)."""

from __future__ import annotations

import importlib.util
import os
import secrets
import string
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import billing_environment
from helpers.cognito_auth import (
    admin_delete_cognito_user,
    mint_native_signup_tokens,
    resolve_student_pool_config_or_skip,
)
from helpers.dsql_audit import admin_connect, execute_scalar, resolve_dsql_endpoint
from helpers.dsql_billing_integration import (
    delete_purchases_for_user,
    delete_webhook_events,
    insert_pending_bundle_purchase,
)

_REPO = Path(__file__).resolve().parents[2]
_FULFILL_SRC = _REPO / "infrastructure" / "lambda" / "billing_fulfillment"
_CATALOG = _REPO / "infrastructure" / "lambda" / "catalog"
_DB_TX_PATH = _CATALOG / "services" / "common" / "db_tx.py"


def _ensure_fulfillment_importable() -> None:
    if "db_tx" not in sys.modules:
        spec = importlib.util.spec_from_file_location("db_tx", _DB_TX_PATH)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["db_tx"] = mod
    if str(_CATALOG) not in sys.path:
        sys.path.insert(0, str(_CATALOG))
    if str(_FULFILL_SRC) not in sys.path:
        sys.path.insert(0, str(_FULFILL_SRC))


_ensure_fulfillment_importable()

from domain_events import BillingDomainEvent  # noqa: E402
from fulfillment_repo import process_event_in_transaction  # noqa: E402

_PROVIDER = "hyperpay"


def _is_dsql_preview_stack() -> bool:
    stack = os.environ.get("INTEGRATION_API_STACK", "").strip()
    return stack.endswith("Api-dsql")


pytestmark = [
    pytest.mark.skipif(
        not resolve_dsql_endpoint(),
        reason="DSQL endpoint not configured (DSQL_ENDPOINT or StreamMyCourse-Dsql-prod)",
    ),
    pytest.mark.skipif(
        not _is_dsql_preview_stack(),
        reason="fulfillment DSQL integration runs only on StreamMyCourse-Api-dsql",
    ),
]


def _email() -> str:
    return f"fulfill-{uuid.uuid4().hex[:12]}@researchspectrum.org"


def _password() -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return f"Rs6!{''.join(secrets.choice(alphabet) for _ in range(20))}aA1"


def _purchase_event(
    *,
    user_sub: str,
    purchase_id: str,
    amount_minor: int,
    event_type: str,
    provider_event_id: str,
) -> BillingDomainEvent:
    return BillingDomainEvent(
        event_type=event_type,
        provider=_PROVIDER,
        provider_event_id=provider_event_id,
        environment=billing_environment(),
        user_sub=user_sub,
        plan_id="",
        payload_digest="a" * 64,
        purchase_id=purchase_id,
        product_type="bundle",
        amount_minor=amount_minor,
        currency="JOD",
        provider_tran_ref=f"INT-{provider_event_id[-12:]}",
    )


def _purchase_status(purchase_id: str) -> str | None:
    with admin_connect() as conn:
        return execute_scalar(
            conn,
            "SELECT status FROM app.purchases WHERE id = %s",
            (purchase_id,),
        )


def _webhook_processed(provider_event_id: str) -> bool:
    with admin_connect() as conn:
        row = execute_scalar(
            conn,
            """
            SELECT processed_at IS NOT NULL
            FROM app.payment_webhook_events
            WHERE provider = %s AND provider_event_id = %s
            """,
            (_PROVIDER, provider_event_id),
        )
    return bool(row)


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


def _throwaway_user_sub(api: ApiClient) -> tuple[str, str]:
    pool = resolve_student_pool_config_or_skip()
    email = _email()
    password = _password()
    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    headers = {"Authorization": f"Bearer {tokens.id_token}"}
    me = api.get_users_me(headers=headers)
    assert me.status_code == 200, me.text
    user_sub = str(me.json().get("userId") or me.json().get("cognitoSub") or "")
    assert user_sub
    return user_sub, email


def test_fulfillment_paid_sets_status_and_processed_at(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    user_sub, email = _throwaway_user_sub(api)
    purchase_id = str(uuid.uuid4())
    event_id = f"integ:paid:{purchase_id}"
    amount_minor = 150_000
    try:
        insert_pending_bundle_purchase(user_sub, amount_minor=amount_minor, purchase_id=purchase_id)
        event = _purchase_event(
            user_sub=user_sub,
            purchase_id=purchase_id,
            amount_minor=amount_minor,
            event_type="purchase.paid",
            provider_event_id=event_id,
        )
        with admin_connect() as conn:
            result = process_event_in_transaction(conn, event)
        assert result.recorded is True
        assert result.purchase_updated is True
        assert _purchase_status(purchase_id) == "paid"
        assert _webhook_processed(event_id)

        replay = _purchase_event(
            user_sub=user_sub,
            purchase_id=purchase_id,
            amount_minor=amount_minor,
            event_type="purchase.paid",
            provider_event_id=event_id,
        )
        with admin_connect() as conn:
            again = process_event_in_transaction(conn, replay)
        assert again.recorded is False
        assert _purchase_status(purchase_id) == "paid"
    finally:
        delete_webhook_events(_PROVIDER, [event_id])
        delete_purchases_for_user(user_sub)
        admin_delete_cognito_user(cfg=pool, username=email)


def test_fulfillment_concurrent_paid_and_failed_one_terminal_status(api: ApiClient) -> None:
    pool = resolve_student_pool_config_or_skip()
    user_sub, email = _throwaway_user_sub(api)
    purchase_id = str(uuid.uuid4())
    paid_event_id = f"integ:concurrent:paid:{purchase_id}"
    fail_event_id = f"integ:concurrent:fail:{purchase_id}"
    amount_minor = 150_000
    outcomes: list[Any] = []
    errors: list[str] = []

    def run(event: BillingDomainEvent) -> None:
        try:
            with admin_connect() as conn:
                outcomes.append(process_event_in_transaction(conn, event))
        except Exception as exc:
            errors.append(str(exc))

    try:
        insert_pending_bundle_purchase(user_sub, amount_minor=amount_minor, purchase_id=purchase_id)
        paid = _purchase_event(
            user_sub=user_sub,
            purchase_id=purchase_id,
            amount_minor=amount_minor,
            event_type="purchase.paid",
            provider_event_id=paid_event_id,
        )
        failed = _purchase_event(
            user_sub=user_sub,
            purchase_id=purchase_id,
            amount_minor=amount_minor,
            event_type="purchase.failed",
            provider_event_id=fail_event_id,
        )
        t1 = threading.Thread(target=run, args=(paid,))
        t2 = threading.Thread(target=run, args=(failed,))
        t1.start()
        t2.start()
        t1.join(timeout=60.0)
        t2.join(timeout=60.0)
        assert not errors, errors
        assert len(outcomes) == 2

        status = _purchase_status(purchase_id)
        assert status in ("paid", "failed")

        with admin_connect() as conn:
            webhook_count = int(
                execute_scalar(
                    conn,
                    """
                    SELECT COUNT(*) FROM app.payment_webhook_events
                    WHERE provider = %s AND provider_event_id IN (%s, %s)
                    """,
                    (_PROVIDER, paid_event_id, fail_event_id),
                )
                or 0
            )
        assert webhook_count == 2
    finally:
        delete_webhook_events(_PROVIDER, [paid_event_id, fail_event_id])
        delete_purchases_for_user(user_sub)
        admin_delete_cognito_user(cfg=pool, username=email)
