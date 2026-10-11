"""Prod full billing flow: checkout-session (HyperPay eu-test) → webhook → purchase paid."""

from __future__ import annotations

import time

import pytest

from helpers.api import ApiClient
from helpers.billing_access import (
    billing_environment,
    build_hyperpay_purchase_notification,
    decode_jwt_sub,
    post_checkout_session,
    post_hyperpay_webhook,
    skip_if_billing_webhook_unavailable,
    skip_if_checkout_unavailable,
    skip_if_hyperpay_webhook_unavailable,
)
from helpers.integration_student import skip_if_integration_student_has_paid_bundle
def _publish_course_with_lesson(
    api: ApiClient,
    course_factory,
    lesson_factory,
    *,
    label: str,
) -> tuple[str, str]:
    course = course_factory(label=label)
    lesson = lesson_factory(course.course_id, label=f"{label}-lesson")
    upload_resp = api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200
    return course.course_id, lesson.lesson_id


def _student_jwt_or_skip() -> str:
    import os

    token = os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT_STUDENT not set")
    return token


def _newest_pending_purchase(student_api: ApiClient) -> tuple[str, int, str, str | None]:
    """Return ``(purchase_id, amount_minor, product_type, course_id)`` for newest pending row."""
    resp = student_api.raw.get("/billing/purchases")
    assert resp.status_code == 200, resp.text[:200]
    purchases = resp.json().get("purchases") or []
    pending = [p for p in purchases if p.get("status") == "pending"]
    if not pending:
        pytest.skip(
            "no pending purchase for ci-student (owns bundle on prod). "
            "Start a checkout in the student UI or use an account without bundle access."
        )
    row = pending[-1]
    return (
        str(row["id"]),
        int(row["amountMinor"]),
        str(row.get("productType") or "bundle"),
        str(row.get("courseId") or "") or None,
    )


def _wait_purchase_paid(student_api: ApiClient, purchase_id: str, *, timeout_sec: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_sec
    last_status = ""
    while time.monotonic() < deadline:
        resp = student_api.raw.get("/billing/purchases")
        assert resp.status_code == 200, resp.text[:200]
        rows = resp.json().get("purchases") or []
        row = next((p for p in rows if str(p.get("id")) == purchase_id), None)
        if row is not None:
            last_status = str(row.get("status") or "")
            if last_status == "paid":
                return
        time.sleep(2)
    pytest.fail(f"purchase {purchase_id} not paid within {timeout_sec}s (last status={last_status!r})")


def test_hyperpay_checkout_session_webhook_marks_purchase_paid(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Checkout (OPPWA eu-test widget) → encrypted PAYMENT webhook → purchase paid in RDS."""
    skip_if_billing_webhook_unavailable()
    jwt = _student_jwt_or_skip()
    user_sub = decode_jwt_sub(jwt)
    env = billing_environment()
    skip_if_integration_student_has_paid_bundle(student_api)

    _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-hyperpay-full-flow"
    )

    checkout = post_checkout_session(student_api, jwt, product_type="bundle")
    skip_if_checkout_unavailable(checkout)

    purchase_id: str | None = None
    amount_minor: int | None = None
    if checkout.status_code == 200:
        body = checkout.json()
        widget = str(body.get("widgetScriptUrl") or "")
        assert "eu-test.oppwa.com" in widget, f"expected eu-test widget URL, got {widget[:120]!r}"
        purchase_id = str(body.get("purchaseId") or "").strip()
        amount_minor = int(body.get("amountMinor"))
        assert body.get("currency") == "JOD"
        assert str(body.get("checkoutId") or "").strip()
    elif checkout.status_code == 409:
        code = str(checkout.json().get("code") or "")
        if code not in ("checkout_in_progress", "already_owned"):
            pytest.fail(f"unexpected checkout 409 code={code!r} body={checkout.text[:200]!r}")
        product_type = "bundle"
        course_id = None
        purchase_id, amount_minor, product_type, course_id = _newest_pending_purchase(student_api)
    else:
        pytest.fail(f"checkout-session failed: {checkout.status_code} {checkout.text[:200]!r}")

    assert purchase_id and amount_minor is not None

    if checkout.status_code == 200:
        product_type = "bundle"
        course_id = None

    notification = build_hyperpay_purchase_notification(
        user_sub,
        environment=env,
        product_type=product_type,
        course_id=course_id,
        purchase_id=purchase_id,
        amount_minor=amount_minor,
    )
    webhook_resp = post_hyperpay_webhook(api_base_url, notification)
    skip_if_hyperpay_webhook_unavailable(webhook_resp)
    assert webhook_resp.status_code == 200, webhook_resp.text[:200]

    _wait_purchase_paid(student_api, purchase_id)
