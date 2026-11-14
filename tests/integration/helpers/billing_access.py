"""Billing / purchase access helpers for HTTPS integration tests (RS-5 / HyperPay).

Uses encrypted HyperPay webhooks on ``POST /webhooks/payments/hyperpay``.
Never log full JWTs, ``HYPERPAY_ACCESS_TOKEN``, or webhook secret values.

Set ``INTEGRATION_HYPERPAY_WEBHOOK_SECRET`` (or ``HYPERPAY_WEBHOOK_SECRET``) to the
same 64-char hex key configured on the billing edge.
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
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from helpers.api import ApiClient

_JOD_FILS_PER_MAJOR = 1000
_DEFAULT_BUNDLE_FILS = 150_000
_WEBHOOK_PATH = "/webhooks/payments/hyperpay"


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
    """Deployment environment segment for cart_id (default ``prod``)."""
    return os.environ.get("INTEGRATION_BILLING_ENV", "prod").strip() or "prod"


def hyperpay_webhook_secret_hex() -> str:
    """Webhook AES key for integration tests (never log the return value)."""
    direct = os.environ.get("INTEGRATION_HYPERPAY_WEBHOOK_SECRET", "").strip()
    if direct:
        return direct
    return os.environ.get("HYPERPAY_WEBHOOK_SECRET", "").strip()


def billing_webhook_disabled_reason() -> str | None:
    """Return skip reason when billing webhook tests are explicitly disabled."""
    flag = os.environ.get("INTEGRATION_BILLING_WEBHOOK", "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return "INTEGRATION_BILLING_WEBHOOK disabled"
    return None


def fils_to_hyperpay_amount(amount_minor: int) -> str:
    """Format whole-JOD fils for HyperPay webhook ``amount`` field."""
    if amount_minor % _JOD_FILS_PER_MAJOR != 0:
        raise ValueError("amount_minor must be whole JOD fils")
    major = amount_minor // _JOD_FILS_PER_MAJOR
    return f"{major}.00"


def build_merchant_transaction_id(
    user_sub: str,
    purchase_id: str,
    *,
    environment: str | None = None,
    product_type: str = "bundle",
    course_id: str | None = None,
) -> str:
    """Build v2 purchase ``merchantTransactionId`` (HyperPay cart metadata)."""
    env = environment or billing_environment()
    if product_type == "course":
        cid = course_id or str(uuid.uuid4())
        return f"v2|{env}|{user_sub}|course|{cid}|{purchase_id}"
    return f"v2|{env}|{user_sub}|bundle|{purchase_id}"


def build_hyperpay_purchase_notification(
    user_sub: str,
    *,
    environment: str | None = None,
    product_type: str = "bundle",
    course_id: str | None = None,
    purchase_id: str | None = None,
    amount_minor: int | None = None,
    payment_id: str | None = None,
    result_code: str = "000.000.000",
) -> dict[str, Any]:
    """Build decrypted HyperPay PAYMENT notification JSON (before AES-GCM wrap)."""
    pid = purchase_id or str(uuid.uuid4())
    fils = amount_minor if amount_minor is not None else _DEFAULT_BUNDLE_FILS
    merchant_tx = build_merchant_transaction_id(
        user_sub,
        pid,
        environment=environment,
        product_type=product_type,
        course_id=course_id,
    )
    pay_id = payment_id or f"MOCK-HP-PAY-{uuid.uuid4().hex[:12]}"
    return {
        "type": "PAYMENT",
        "action": "CREATED",
        "payload": {
            "id": pay_id,
            "paymentType": "DB",
            "amount": fils_to_hyperpay_amount(fils),
            "currency": "JOD",
            "merchantTransactionId": merchant_tx,
            "result": {"code": result_code, "description": "Transaction succeeded"},
        },
    }


def encrypt_hyperpay_notification(
    payload: dict[str, Any],
    *,
    webhook_secret_hex: str,
    iv_hex: str = "000000000000000000000000",
) -> tuple[str, str, str]:
    """Return ``(body_hex, iv_hex, tag_hex)`` for HyperPay webhook POST."""
    key = bytes.fromhex(webhook_secret_hex)
    iv = bytes.fromhex(iv_hex)
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, None)
    ciphertext = ciphertext_with_tag[:-16]
    tag = ciphertext_with_tag[-16:]
    return ciphertext.hex(), iv.hex(), tag.hex()


def post_hyperpay_webhook(
    api_base_url: str,
    notification: dict[str, Any],
    *,
    webhook_secret_hex: str | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST encrypted HyperPay webhook (no auth)."""
    secret = (webhook_secret_hex or hyperpay_webhook_secret_hex()).strip()
    if not secret:
        pytest.skip(
            "INTEGRATION_HYPERPAY_WEBHOOK_SECRET (or HYPERPAY_WEBHOOK_SECRET) not set"
        )
    body_hex, iv_hex, tag_hex = encrypt_hyperpay_notification(
        notification, webhook_secret_hex=secret
    )
    url = f"{api_base_url.rstrip('/')}{_WEBHOOK_PATH}"
    with httpx.Client(timeout=timeout_sec) as client:
        return client.post(
            url,
            content=body_hex,
            headers={
                "Content-Type": "application/json",
                "X-Initialization-Vector": iv_hex,
                "X-Authentication-Tag": tag_hex,
            },
        )


def post_hyperpay_webhook_probe(api_base_url: str, *, timeout_sec: float = 30.0) -> httpx.Response:
    """POST ignored notification type to verify webhook decrypt without granting access."""
    notification = {"type": "REGISTRATION", "action": "CREATED", "payload": {}}
    return post_hyperpay_webhook(api_base_url, notification, timeout_sec=timeout_sec)


def post_mock_purchase_paid(
    api_base_url: str,
    user_sub: str,
    *,
    environment: str | None = None,
    product_type: str = "bundle",
    course_id: str | None = None,
    purchase_id: str | None = None,
    amount_minor: int | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST mock purchase-paid HyperPay webhook (RS-5). Requires pending purchase row in RDS."""
    notification = build_hyperpay_purchase_notification(
        user_sub,
        environment=environment,
        product_type=product_type,
        course_id=course_id,
        purchase_id=purchase_id,
        amount_minor=amount_minor,
    )
    return post_hyperpay_webhook(
        api_base_url, notification, timeout_sec=timeout_sec
    )


def wait_for_subscription_access(
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    timeout_sec: float = 30.0,
    poll_interval_sec: float = 1.0,
) -> None:
    """Poll playback until access is granted (not 403 purchase_required)."""
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
            if last_code not in ("purchase_required", "subscription_required"):
                last_text = resp.text[:200]
                break
        else:
            last_text = resp.text[:200]
            break
        time.sleep(poll_interval_sec)
    pytest.fail(
        "Timed out waiting for purchase access via playback: "
        f"last_status={last_status} last_code={last_code!r} body={last_text!r}"
    )


def wait_for_playback_purchase_required(
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    timeout_sec: float = 30.0,
    poll_interval_sec: float = 1.0,
) -> None:
    """Poll playback until 403 purchase_required (async fulfillment after webhook)."""
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
            if last_code in ("purchase_required", "subscription_required"):
                return
            pytest.fail(
                "Expected 403 purchase_required on playback, got "
                f"code={last_code!r} body={last_text!r}"
            )
        if resp.status_code != 200:
            pytest.fail(
                f"Unexpected playback status while waiting for purchase_required: "
                f"{resp.status_code} body={last_text!r}"
            )
        time.sleep(poll_interval_sec)
    pytest.fail(
        "Timed out waiting for lapsed subscription to deny playback (still 200): "
        f"last_status={last_status} body={last_text!r}"
    )


def skip_if_billing_webhook_unavailable() -> None:
    """Skip when billing webhook integration is explicitly disabled via env."""
    reason = billing_webhook_disabled_reason()
    if reason:
        pytest.skip(reason)


def skip_if_checkout_unavailable(resp: httpx.Response) -> None:
    """Skip when checkout/manage route is missing or billing is not configured."""
    if resp.status_code == 404:
        pytest.skip("billing route not deployed (404)")
    if resp.status_code == 503:
        try:
            code = resp.json().get("code")
        except Exception:
            code = None
        if code == "billing_unconfigured":
            pytest.skip("billing not configured on API (503 billing_unconfigured)")


def skip_if_hyperpay_webhook_unavailable(resp: httpx.Response) -> None:
    """Skip when HyperPay webhook cannot be accepted (404/503/401/other)."""
    if resp.status_code == 404:
        pytest.skip("HyperPay webhook route not deployed (404)")
    if resp.status_code == 503:
        try:
            code = resp.json().get("code")
        except Exception:
            code = None
        if code == "billing_unconfigured":
            pytest.skip("billing not configured on API (503 billing_unconfigured)")
    if resp.status_code == 401:
        pytest.skip(
            "HyperPay webhook decrypt failed (401) — check INTEGRATION_HYPERPAY_WEBHOOK_SECRET"
        )
    if resp.status_code != 200:
        pytest.skip(
            f"HyperPay webhook probe failed (HTTP {resp.status_code}): {resp.text[:200]}"
        )


def _pending_bundle_purchase(
    student_api: ApiClient,
    *,
    timeout_sec: float = 30.0,
) -> tuple[str, int]:
    """Return ``(purchase_id, amount_minor)`` for the newest pending bundle checkout."""
    resp = student_api.raw.get("/billing/purchases", timeout=timeout_sec)
    if resp.status_code == 404:
        pytest.skip("GET /billing/purchases not deployed (404)")
    if resp.status_code != 200:
        pytest.fail(
            f"GET /billing/purchases failed: status={resp.status_code} body={resp.text[:200]!r}"
        )
    purchases = resp.json().get("purchases") or []
    pending = [
        p
        for p in purchases
        if p.get("productType") == "bundle" and p.get("status") == "pending"
    ]
    if not pending:
        pytest.fail("no pending bundle purchase after checkout-session")
    row = pending[-1]
    return str(row["id"]), int(row["amountMinor"])


# OPPWA-required billing contact (HyperPay onboarding email); integration default only.
_DEFAULT_CHECKOUT_BILLING: dict[str, str] = {
    "givenName": "Integration",
    "surname": "Student",
    "street": "1 Test Street",
    "city": "Amman",
    "state": "Amman",
    "postcode": "11118",
    "country": "JO",
}


def post_checkout_session(
    student_api: ApiClient,
    jwt: str,
    *,
    product_type: str = "bundle",
    course_id: str | None = None,
    plan_id: str | None = None,
    billing: dict[str, str] | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """POST ``/billing/checkout-session`` as the student (``jwt`` is not logged)."""
    _ = jwt
    _ = plan_id
    body: dict[str, Any] = {
        "productType": product_type,
        "billing": billing if billing is not None else dict(_DEFAULT_CHECKOUT_BILLING),
    }
    if product_type == "course":
        if not course_id:
            raise ValueError("course_id is required when product_type is course")
        body["courseId"] = course_id
    return student_api.raw.post(
        "/billing/checkout-session",
        json=body,
        timeout=timeout_sec,
    )


def _assert_checkout_session_body(body: dict[str, Any]) -> None:
    checkout_id = str(body.get("checkoutId") or "").strip()
    if not checkout_id:
        pytest.fail("checkout-session 200 missing checkoutId")
    currency = str(body.get("currency") or "").strip().upper()
    if currency != "JOD":
        pytest.fail(f"checkout-session expected currency JOD, got {currency!r}")
    if body.get("amountMinor") is None:
        pytest.fail("checkout-session 200 missing amountMinor")


def _checkout_bundle_and_mock_webhook(
    api_base_url: str,
    student_api: ApiClient,
    jwt: str,
    user_sub: str,
    *,
    environment: str | None = None,
    timeout_sec: float = 30.0,
) -> None:
    checkout_resp = post_checkout_session(
        student_api, jwt, product_type="bundle", timeout_sec=timeout_sec
    )
    skip_if_checkout_unavailable(checkout_resp)
    purchase_id: str | None = None
    amount_minor: int | None = None
    if checkout_resp.status_code == 409:
        code = str(checkout_resp.json().get("code") or "")
        if code == "already_owned":
            return
        if code != "checkout_in_progress":
            pytest.fail(
                "checkout-session failed: "
                f"status={checkout_resp.status_code} body={checkout_resp.text[:200]!r}"
            )
    elif checkout_resp.status_code != 200:
        pytest.fail(
            "checkout-session failed: "
            f"status={checkout_resp.status_code} body={checkout_resp.text[:200]!r}"
        )
    else:
        checkout_body = checkout_resp.json()
        _assert_checkout_session_body(checkout_body)
        resp_purchase_id = str(checkout_body.get("purchaseId") or "").strip()
        resp_amount_minor = checkout_body.get("amountMinor")
        if resp_purchase_id and resp_amount_minor is not None:
            purchase_id = resp_purchase_id
            amount_minor = int(resp_amount_minor)

    if not purchase_id or amount_minor is None:
        purchase_id, amount_minor = _pending_bundle_purchase(
            student_api, timeout_sec=timeout_sec
        )

    webhook_resp = post_mock_purchase_paid(
        api_base_url,
        user_sub,
        environment=environment,
        purchase_id=purchase_id,
        amount_minor=amount_minor,
        timeout_sec=timeout_sec,
    )
    skip_if_hyperpay_webhook_unavailable(webhook_resp)


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
    """Mock bundle checkout → HyperPay webhook → poll playback until access is granted."""
    _ = plan_id
    skip_if_billing_webhook_unavailable()

    user_sub = decode_jwt_sub(jwt)
    probe = student_api.get_playback(course_id, lesson_id)
    if probe.status_code == 200:
        return

    _checkout_bundle_and_mock_webhook(
        api_base_url,
        student_api,
        jwt,
        user_sub,
        environment=environment,
        timeout_sec=timeout_sec,
    )

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
    """Skip negative (no-sub) tests when shared integration env already granted access."""
    resp = student_api.get_playback(course_id, lesson_id)
    if resp.status_code == 200:
        pytest.skip("student already has bundle/course access (shared prod state)")


def ensure_student_subscription(
    api_base_url: str,
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    environment: str | None = None,
) -> str:
    """Grant course access via bundle checkout + mock HyperPay webhook (RS-5).

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

    _checkout_bundle_and_mock_webhook(
        api_base_url,
        student_api,
        token,
        user_sub,
        environment=environment,
    )

    wait_for_subscription_access(student_api, course_id, lesson_id)
    return user_sub


# --- Legacy aliases (subscription-era names; purchase flow underneath) ---

def skip_if_mock_ipn_unavailable(resp: httpx.Response) -> None:
    """Alias for ``skip_if_hyperpay_webhook_unavailable``."""
    skip_if_hyperpay_webhook_unavailable(resp)


def post_mock_subscription_activated(
    api_base_url: str,
    user_sub: str,
    *,
    environment: str | None = None,
    plan_id: str | None = None,
    timeout_sec: float = 30.0,
) -> httpx.Response:
    """Legacy name — posts a non-purchase webhook probe (no access grant).

    Callers that need playback access should use ``ensure_student_subscription``.
    """
    _ = user_sub, environment, plan_id
    return post_hyperpay_webhook_probe(api_base_url, timeout_sec=timeout_sec)
