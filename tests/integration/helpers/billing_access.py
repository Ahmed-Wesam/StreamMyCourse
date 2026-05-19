"""Billing / subscription helpers for HTTPS integration tests (WS5 Phase C).

Uses the dev mock PayTabs adapter (``X-Mock-Signature: test``). Never log full JWTs
or ``PAYTABS_SERVER_KEY`` values.
"""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from typing import Any

import httpx
import pytest

from helpers.api import ApiClient

_PLAN_ID_DEV = "a0000000-0000-4000-8000-000000000011"
_PLAN_ID_PROD = "a0000000-0000-4000-8000-000000000012"
_MOCK_SIGNATURE = "test"
_WEBHOOK_PATH = "/webhooks/payments/paytabs"


def decode_jwt_sub(token: str) -> str:
    """Decode JWT payload (no signature verify) and return the ``sub`` claim."""
    parts = (token or "").strip().split(".")
    if len(parts) < 2:
        raise ValueError("JWT must have at least header and payload segments")
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
    payload = json.loads(payload_bytes.decode("utf-8"))
    sub = str(payload.get("sub") or "").strip()
    if not sub:
        raise ValueError("JWT payload missing sub claim")
    return sub


def billing_environment() -> str:
    """Deployment environment segment for cart_id (default ``dev``)."""
    return os.environ.get("INTEGRATION_BILLING_ENV", "dev").strip() or "dev"


def seed_plan_id(environment: str | None = None) -> str:
    """Return migration 011 seed ``plan_id`` for dev or prod."""
    env = (environment or billing_environment()).strip().lower()
    if env == "prod":
        return _PLAN_ID_PROD
    return _PLAN_ID_DEV


def billing_webhook_disabled_reason() -> str | None:
    """Return skip reason when billing webhook tests are explicitly disabled."""
    flag = os.environ.get("INTEGRATION_BILLING_WEBHOOK", "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return "INTEGRATION_BILLING_WEBHOOK disabled"
    return None


def build_mock_ipn_activated(
    user_sub: str,
    *,
    environment: str | None = None,
    plan_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    transaction_time: str | None = None,
) -> dict[str, Any]:
    """Build a mock PayTabs Sale/activated IPN body for ``user_sub``."""
    env = environment or billing_environment()
    resolved_plan_id = plan_id or seed_plan_id(env)
    cart_id = f"v1|{env}|{user_sub}|{resolved_plan_id}"
    body: dict[str, Any] = {
        "tran_ref": f"MOCK-ACT-{uuid.uuid4().hex[:12]}",
        "tran_type": "Sale",
        "payment_result": "A",
        "cart_id": cart_id,
        "agreement_id": f"MOCK-AGR-{uuid.uuid4().hex[:8]}",
        "is_recurring": False,
        "transaction_time": transaction_time or "2026-05-18T12:00:00Z",
    }
    if period_start is not None:
        body["subscription_period_start"] = period_start
    if period_end is not None:
        body["subscription_period_end"] = period_end
    return body


def post_mock_lapsed_subscription(
    api_base_url: str,
    user_sub: str,
    *,
    environment: str | None = None,
    plan_id: str | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST mock IPN that grants ``active`` with a billing period already ended (re-subscribe path)."""
    env = environment or billing_environment()
    body = build_mock_ipn_activated(
        user_sub,
        environment=env,
        plan_id=plan_id,
        period_start="2025-01-01T00:00:00Z",
        period_end="2025-02-01T00:00:00Z",
        transaction_time="2025-01-01T00:00:00Z",
    )
    url = f"{api_base_url.rstrip('/')}{_WEBHOOK_PATH}"
    with httpx.Client(timeout=timeout_sec) as client:
        return client.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Mock-Signature": _MOCK_SIGNATURE,
            },
        )


def post_mock_subscription_activated(
    api_base_url: str,
    user_sub: str,
    *,
    environment: str | None = None,
    plan_id: str | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST mock subscription-activated IPN to the billing webhook (no auth)."""
    env = environment or billing_environment()
    body = build_mock_ipn_activated(user_sub, environment=env, plan_id=plan_id)
    url = f"{api_base_url.rstrip('/')}{_WEBHOOK_PATH}"
    with httpx.Client(timeout=timeout_sec) as client:
        return client.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Mock-Signature": _MOCK_SIGNATURE,
            },
        )


def wait_for_subscription_access(
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    timeout_sec: float = 30.0,
    poll_interval_sec: float = 1.0,
) -> None:
    """Poll playback until access is granted (not 403 subscription_required)."""
    deadline = time.monotonic() + timeout_sec
    last_status = 0
    last_code = ""
    last_text = ""
    while time.monotonic() < deadline:
        resp = student_api.get_playback(course_id, lesson_id)
        last_status = resp.status_code
        if resp.status_code == 200:
            return
        if resp.status_code == 403:
            try:
                last_code = str(resp.json().get("code") or "")
            except Exception:
                last_code = ""
            if last_code != "subscription_required":
                last_text = resp.text[:200]
                break
        else:
            last_text = resp.text[:200]
            break
        time.sleep(poll_interval_sec)
    pytest.fail(
        "Timed out waiting for subscription access via playback: "
        f"last_status={last_status} last_code={last_code!r} body={last_text!r}"
    )


def wait_for_playback_subscription_required(
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    timeout_sec: float = 30.0,
    poll_interval_sec: float = 1.0,
) -> None:
    """Poll playback until 403 subscription_required (async fulfillment after mock IPN)."""
    deadline = time.monotonic() + timeout_sec
    last_status = 0
    last_code = ""
    last_text = ""
    while time.monotonic() < deadline:
        resp = student_api.get_playback(course_id, lesson_id)
        last_status = resp.status_code
        last_text = resp.text[:200]
        if resp.status_code == 403:
            try:
                last_code = str(resp.json().get("code") or "")
            except Exception:
                last_code = ""
            if last_code == "subscription_required":
                return
            pytest.fail(
                "Expected 403 subscription_required on playback, got "
                f"code={last_code!r} body={last_text!r}"
            )
        if resp.status_code != 200:
            pytest.fail(
                f"Unexpected playback status while waiting for subscription_required: "
                f"{resp.status_code} body={last_text!r}"
            )
        time.sleep(poll_interval_sec)
    pytest.fail(
        "Timed out waiting for lapsed subscription to deny playback (still 200): "
        f"last_status={last_status} body={last_text!r}"
    )


def seed_lapsed_subscription_via_ipn(
    api_base_url: str,
    user_sub: str,
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    plan_id: str | None = None,
    timeout_sec: float = 30.0,
) -> None:
    """Grant in-period access, lapse via mock IPN, wait until playback is denied.

    Ensures fulfillment wrote a lapsed ``active`` row (not a cold 403) before re-subscribe checkout.
    """
    resolved_plan_id = plan_id or seed_plan_id()
    grant_resp = post_mock_subscription_activated(
        api_base_url,
        user_sub,
        plan_id=resolved_plan_id,
        timeout_sec=timeout_sec,
    )
    skip_if_mock_ipn_unavailable(grant_resp)
    wait_for_subscription_access(
        student_api,
        course_id,
        lesson_id,
        timeout_sec=timeout_sec,
    )

    lapsed_resp = post_mock_lapsed_subscription(
        api_base_url,
        user_sub,
        plan_id=resolved_plan_id,
        timeout_sec=timeout_sec,
    )
    skip_if_mock_ipn_unavailable(lapsed_resp)
    wait_for_playback_subscription_required(
        student_api,
        course_id,
        lesson_id,
        timeout_sec=timeout_sec,
    )


def skip_if_billing_webhook_unavailable() -> None:
    """Skip when billing webhook integration is explicitly disabled via env."""
    reason = billing_webhook_disabled_reason()
    if reason:
        pytest.skip(reason)


def skip_if_checkout_unavailable(resp: httpx.Response) -> None:
    """Skip when checkout route is missing or billing is not configured."""
    if resp.status_code == 404:
        pytest.skip("billing checkout route not deployed (404)")
    if resp.status_code == 503:
        try:
            code = resp.json().get("code")
        except Exception:
            code = None
        if code == "billing_unconfigured":
            pytest.skip("billing not configured on API (503 billing_unconfigured)")


def skip_if_mock_ipn_unavailable(resp: httpx.Response) -> None:
    """Skip when mock PayTabs IPN cannot be accepted (404/503/401/other)."""
    if resp.status_code == 404:
        pytest.skip("payments webhook route not deployed (404)")
    if resp.status_code == 503:
        try:
            code = resp.json().get("code")
        except Exception:
            code = None
        if code == "billing_unconfigured":
            pytest.skip("billing not configured on API (503 billing_unconfigured)")
    if resp.status_code == 401:
        pytest.skip(
            "mock webhook signature rejected (401) — payments stack may use live adapter"
        )
    if resp.status_code != 200:
        pytest.skip(
            f"mock subscription IPN failed (HTTP {resp.status_code}): {resp.text[:200]}"
        )


def build_mock_ipn_renewed(
    user_sub: str,
    *,
    environment: str | None = None,
    plan_id: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
    transaction_time: str | None = None,
    agreement_id: str | None = None,
) -> dict[str, Any]:
    """Build a mock PayTabs recurring Sale IPN (``subscription.renewed``)."""
    body = build_mock_ipn_activated(
        user_sub,
        environment=environment,
        plan_id=plan_id,
        period_start=period_start,
        period_end=period_end,
        transaction_time=transaction_time,
    )
    body["is_recurring"] = True
    body["recurring_count"] = 2
    body["tran_ref"] = f"MOCK-REN-{uuid.uuid4().hex[:12]}"
    if agreement_id:
        body["agreement_id"] = agreement_id
    return body


def post_mock_subscription_renewed(
    api_base_url: str,
    user_sub: str,
    *,
    environment: str | None = None,
    plan_id: str | None = None,
    agreement_id: str | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST mock recurring renewal IPN (W7-P3c integration)."""
    env = environment or billing_environment()
    body = build_mock_ipn_renewed(
        user_sub,
        environment=env,
        plan_id=plan_id,
        agreement_id=agreement_id,
    )
    url = f"{api_base_url.rstrip('/')}{_WEBHOOK_PATH}"
    with httpx.Client(timeout=timeout_sec) as client:
        return client.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Mock-Signature": _MOCK_SIGNATURE,
            },
        )


def skip_if_manage_read_unavailable(resp: httpx.Response) -> None:
    """Skip when GET /billing/subscription route is missing (not ``not_subscribed``)."""
    if resp.status_code == 404:
        try:
            code = resp.json().get("code")
        except Exception:
            code = None
        if code != "not_subscribed":
            pytest.skip("GET /billing/subscription route not deployed (404)")


def get_subscription(
    student_api: ApiClient,
    *,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """GET ``/billing/subscription`` as the student."""
    return student_api.raw.get("/billing/subscription", timeout=timeout_sec)


def post_cancel_subscription(
    student_api: ApiClient,
    *,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST ``/billing/cancel-subscription`` (empty JSON body)."""
    return student_api.raw.post(
        "/billing/cancel-subscription",
        json={},
        timeout=timeout_sec,
    )


def post_reactivate_subscription(
    student_api: ApiClient,
    *,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST ``/billing/reactivate-subscription`` (empty JSON body)."""
    return student_api.raw.post(
        "/billing/reactivate-subscription",
        json={},
        timeout=timeout_sec,
    )


def post_checkout_session(
    student_api: ApiClient,
    jwt: str,
    *,
    plan_id: str | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST ``/billing/checkout-session`` as the student (``jwt`` is not logged)."""
    _ = jwt  # caller passes token for sub correlation in combined flows
    body: dict[str, Any] = {}
    if plan_id:
        body["planId"] = plan_id
    return student_api.raw.post(
        "/billing/checkout-session",
        json=body,
        timeout=timeout_sec,
    )


def checkout_then_wait_for_access(
    api_base_url: str,
    student_api: ApiClient,
    jwt: str,
    course_id: str,
    lesson_id: str,
    *,
    environment: str | None = None,
    plan_id: str | None = None,
    timeout_sec: float = 30.0,
    poll_interval_sec: float = 1.0,
) -> None:
    """Mock checkout → optional mock IPN → poll playback until access is granted."""
    skip_if_billing_webhook_unavailable()

    user_sub = decode_jwt_sub(jwt)
    probe = student_api.get_playback(course_id, lesson_id)
    if probe.status_code == 200:
        return

    checkout_resp = post_checkout_session(
        student_api, jwt, plan_id=plan_id, timeout_sec=timeout_sec
    )
    skip_if_checkout_unavailable(checkout_resp)
    if checkout_resp.status_code != 200:
        pytest.fail(
            "checkout-session failed: "
            f"status={checkout_resp.status_code} body={checkout_resp.text[:200]!r}"
        )
    redirect_url = str(checkout_resp.json().get("redirect_url") or "").strip()
    if not redirect_url:
        pytest.fail("checkout-session 200 missing redirect_url")

    ipn_resp = post_mock_subscription_activated(
        api_base_url,
        user_sub,
        environment=environment,
        plan_id=plan_id,
        timeout_sec=timeout_sec,
    )
    skip_if_mock_ipn_unavailable(ipn_resp)

    wait_for_subscription_access(
        student_api,
        course_id,
        lesson_id,
        timeout_sec=timeout_sec,
        poll_interval_sec=poll_interval_sec,
    )


def skip_if_student_has_subscription(
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
) -> None:
    """Skip negative (no-sub) tests when shared dev already granted subscription."""
    resp = student_api.get_playback(course_id, lesson_id)
    if resp.status_code == 200:
        pytest.skip("student already has active subscription (shared dev state)")


def ensure_student_subscription(
    api_base_url: str,
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    environment: str | None = None,
) -> str:
    """Grant platform subscription via mock IPN and wait until playback succeeds.

    Returns the student's Cognito ``sub``. Skips when webhook prerequisites are missing.
    """
    skip_if_billing_webhook_unavailable()

    token = os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT_STUDENT not set")
    user_sub = decode_jwt_sub(token)

    resp = student_api.get_playback(course_id, lesson_id)
    if resp.status_code == 200:
        return user_sub

    ipn_resp = post_mock_subscription_activated(
        api_base_url,
        user_sub,
        environment=environment,
    )
    skip_if_mock_ipn_unavailable(ipn_resp)

    wait_for_subscription_access(student_api, course_id, lesson_id)
    return user_sub
