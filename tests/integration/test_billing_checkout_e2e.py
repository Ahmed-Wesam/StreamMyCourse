"""Checkout session → mock IPN → playback (WS6 W6-P10)."""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import (
    checkout_then_wait_for_access,
    decode_jwt_sub,
    ensure_student_subscription,
    post_checkout_session,
    post_mock_subscription_activated,
    seed_lapsed_subscription_via_ipn,
    seed_plan_id,
    skip_if_billing_webhook_unavailable,
    skip_if_checkout_unavailable,
    skip_if_mock_ipn_unavailable,
    skip_if_student_has_subscription,
    wait_for_subscription_access,
)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    """Skip (not exit) when integration API URL is unset — allows isolated pytest runs."""
    value = os.environ.get("INTEGRATION_API_BASE_URL", "").strip()
    if not value:
        pytest.skip("INTEGRATION_API_BASE_URL not set — see tests/integration/README.md")
    return value.rstrip("/")


@pytest.fixture(scope="session")
def video_bucket() -> str:
    value = os.environ.get("INTEGRATION_VIDEO_BUCKET", "").strip()
    if not value:
        pytest.skip("INTEGRATION_VIDEO_BUCKET not set — see tests/integration/README.md")
    return value


@pytest.fixture(scope="session")
def http_client(api_base_url: str) -> Iterator[httpx.Client]:
    default_headers: dict[str, str] = {}
    token = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT not set (teacher principal for course setup)")
    default_headers["Authorization"] = f"Bearer {token}"
    with httpx.Client(
        base_url=api_base_url, timeout=30.0, headers=default_headers
    ) as client:
        yield client


@pytest.fixture(scope="session")
def student_http_client(api_base_url: str) -> Iterator[httpx.Client]:
    token = os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT_STUDENT not set")
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=api_base_url, timeout=30.0, headers=headers) as client:
        yield client


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
    token = os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT_STUDENT not set")
    return token


def _probe_mock_webhook(api_base_url: str) -> httpx.Response:
    """POST an ignored mock IPN type to verify mock signature without granting access."""
    url = f"{api_base_url.rstrip('/')}/webhooks/payments/paytabs"
    body = {
        "tran_ref": "MOCK-PROBE-001",
        "tran_type": "Refund",
        "payment_result": "A",
        "cart_id": "v1|dev|probe-user|00000000-0000-4000-8000-000000000001",
    }
    with httpx.Client(timeout=30.0) as client:
        return client.post(
            url,
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Mock-Signature": "test",
            },
        )


def test_checkout_session_then_ipn_grants_playback(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """POST checkout (mock redirect) → mock IPN → GET playback returns 200."""
    skip_if_billing_webhook_unavailable()
    jwt = _student_jwt_or_skip()
    user_sub = decode_jwt_sub(jwt)
    plan_id = seed_plan_id()

    # Prior run may have left a fresh incomplete row on the shared dev student.
    stale = post_checkout_session(student_api, jwt, plan_id=plan_id)
    if stale.status_code == 409 and stale.json().get("code") == "checkout_in_progress":
        ipn = post_mock_subscription_activated(api_base_url, user_sub, plan_id=plan_id)
        skip_if_mock_ipn_unavailable(ipn)

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-checkout-e2e"
    )
    skip_if_student_has_subscription(student_api, course_id, lesson_id)

    checkout_then_wait_for_access(
        api_base_url,
        student_api,
        jwt,
        course_id,
        lesson_id,
        plan_id=plan_id,
    )

    playback_resp = student_api.get_playback(course_id, lesson_id)
    assert playback_resp.status_code == 200, playback_resp.text
    body = playback_resp.json()
    assert isinstance(body.get("url"), str) and body["url"]


def test_checkout_session_already_subscribed_returns_409(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Student with granting subscription row receives 409 already_subscribed on checkout."""
    skip_if_billing_webhook_unavailable()
    jwt = _student_jwt_or_skip()

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-checkout-409"
    )
    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

    checkout_resp = post_checkout_session(student_api, jwt, plan_id=seed_plan_id())
    skip_if_checkout_unavailable(checkout_resp)

    assert checkout_resp.status_code == 409, (
        f"Expected 409 already_subscribed, got {checkout_resp.status_code}: "
        f"{checkout_resp.text[:200]}"
    )
    assert checkout_resp.json().get("code") == "already_subscribed"


def test_zz_second_checkout_while_incomplete_returns_checkout_in_progress(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Back-to-back checkout without IPN leaves incomplete row; second call is 409 not 503."""
    skip_if_billing_webhook_unavailable()
    jwt = _student_jwt_or_skip()

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-checkout-in-progress"
    )
    skip_if_student_has_subscription(student_api, course_id, lesson_id)

    plan_id = seed_plan_id()
    first = post_checkout_session(student_api, jwt, plan_id=plan_id)
    skip_if_checkout_unavailable(first)
    if first.status_code == 409 and first.json().get("code") == "checkout_in_progress":
        # Shared dev student may still have a fresh incomplete row from a prior run or test.
        user_sub = decode_jwt_sub(jwt)
        seed_lapsed_subscription_via_ipn(
            api_base_url,
            user_sub,
            student_api,
            course_id,
            lesson_id,
            plan_id=plan_id,
        )
        first = post_checkout_session(student_api, jwt, plan_id=plan_id)
        skip_if_checkout_unavailable(first)
    assert first.status_code == 200, first.text[:200]

    second = post_checkout_session(student_api, jwt, plan_id=seed_plan_id())
    skip_if_checkout_unavailable(second)
    assert second.status_code == 409, (
        f"Expected 409 checkout_in_progress, got {second.status_code}: {second.text[:200]}"
    )
    assert second.json().get("code") == "checkout_in_progress"


def test_z_checkout_after_lapsed_active_subscription_returns_200(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Lapsed active row (period ended) reopens to incomplete; checkout is 200 not 409/503."""
    skip_if_billing_webhook_unavailable()
    jwt = _student_jwt_or_skip()
    user_sub = decode_jwt_sub(jwt)
    plan_id = seed_plan_id()

    # Skip before creating an incomplete row when mock IPN is unavailable (breaks test_zz_second_*).
    skip_if_mock_ipn_unavailable(_probe_mock_webhook(api_base_url))

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-checkout-lapsed"
    )

    seed_lapsed_subscription_via_ipn(
        api_base_url,
        user_sub,
        student_api,
        course_id,
        lesson_id,
        plan_id=plan_id,
    )

    try:
        checkout_resp = post_checkout_session(student_api, jwt, plan_id=plan_id)
        skip_if_checkout_unavailable(checkout_resp)
        assert checkout_resp.status_code == 200, (
            f"Expected 200 checkout for lapsed active re-subscribe, got "
            f"{checkout_resp.status_code}: {checkout_resp.text[:200]}"
        )
        body = checkout_resp.json()
        assert isinstance(body.get("redirect_url"), str) and body["redirect_url"].strip()
    finally:
        restore_resp = post_mock_subscription_activated(
            api_base_url, user_sub, plan_id=plan_id
        )
        if restore_resp.status_code == 200:
            wait_for_subscription_access(student_api, course_id, lesson_id)
