"""Subscription manage E2E: mock subscribe → cancel → access until period end (WS8 W8-P10).

Flow exercises the deployed billing edge + catalog path without reactivate (removed in WS8).

**Provider cancel:** After catalog cancel-at-period-end, billing edge calls
``PaymentProviderPort.cancel_agreement``. The dev mock adapter is a no-op (no outbound HTTP);
unit tests assert the handler invokes the port (``test_billing_edge_cancel_calls_provider``).
This suite cannot spy the adapter—treat cancel **200** (not **502** ``provider_cancel_failed``)
as evidence the provider step completed on stacks with WS8 wired.

Skips when integration env is unset (same pattern as ``test_billing_checkout_e2e.py``).
"""

from __future__ import annotations

import os
from typing import Iterator

import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import (
    decode_jwt_sub,
    ensure_student_subscription,
    get_subscription,
    post_cancel_subscription,
    post_checkout_session,
    post_mock_subscription_activated,
    seed_plan_id,
    skip_if_billing_webhook_unavailable,
    skip_if_checkout_unavailable,
    skip_if_manage_read_unavailable,
    skip_if_mock_ipn_unavailable,
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


@pytest.fixture
def api(http_client: httpx.Client) -> ApiClient:
    return ApiClient(http_client)


@pytest.fixture
def student_api(student_http_client: httpx.Client) -> ApiClient:
    return ApiClient(student_http_client)


@pytest.fixture
def course_factory(api: ApiClient, request: pytest.FixtureRequest):
    from helpers.factories import build_course_factory

    created_course_ids: list[str] = []

    def register(course_id: str) -> None:
        created_course_ids.append(course_id)

    factory = build_course_factory(api, register)

    def cleanup() -> None:
        for course_id in created_course_ids:
            try:
                api.delete_course(course_id)
            except Exception:
                pass

    request.addfinalizer(cleanup)
    return factory


@pytest.fixture
def lesson_factory(api: ApiClient):
    from helpers.factories import build_lesson_factory

    return build_lesson_factory(api)


def _student_jwt_or_skip() -> str:
    token = os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT_STUDENT not set")
    return token


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


def _probe_mock_webhook(api_base_url: str) -> httpx.Response:
    """POST an ignored mock IPN type to verify mock signature without granting access."""
    url = f"{api_base_url.rstrip('/')}/webhooks/payments/paytabs"
    body = {
        "tran_ref": "MOCK-PROBE-MANAGE-001",
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


def _restore_active_subscription(
    api_base_url: str,
    user_sub: str,
    student_api: ApiClient,
    course_id: str,
    lesson_id: str,
    *,
    plan_id: str,
) -> None:
    """Best-effort restore shared dev student to active after manage mutations."""
    restore = post_mock_subscription_activated(
        api_base_url, user_sub, plan_id=plan_id
    )
    if restore.status_code == 200:
        wait_for_subscription_access(student_api, course_id, lesson_id)


def test_mock_subscribe_cancel_preserves_playback_and_blocks_checkout(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Mock IPN subscribe → cancel (provider step) → playback 200 → checkout 409."""
    skip_if_billing_webhook_unavailable()
    skip_if_mock_ipn_unavailable(_probe_mock_webhook(api_base_url))
    jwt = _student_jwt_or_skip()
    user_sub = decode_jwt_sub(jwt)
    plan_id = seed_plan_id()

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-manage-e2e"
    )

    try:
        ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

        sub_resp = get_subscription(student_api)
        skip_if_manage_read_unavailable(sub_resp)
        assert sub_resp.status_code == 200, sub_resp.text[:200]
        sub_before = sub_resp.json()
        assert sub_before.get("canCancel") is True, sub_before
        assert sub_before.get("cancelAtPeriodEnd") is False

        cancel_resp = post_cancel_subscription(student_api)
        skip_if_checkout_unavailable(cancel_resp)
        assert cancel_resp.status_code == 200, (
            f"Expected cancel 200 (provider cancel_agreement on WS8 stacks), got "
            f"{cancel_resp.status_code}: {cancel_resp.text[:200]}"
        )
        cancel_body = cancel_resp.json()
        assert cancel_body.get("cancelAtPeriodEnd") is True

        playback_resp = student_api.get_playback(course_id, lesson_id)
        assert playback_resp.status_code == 200, playback_resp.text[:200]

        sub_canceled = get_subscription(student_api)
        skip_if_manage_read_unavailable(sub_canceled)
        assert sub_canceled.status_code == 200, sub_canceled.text[:200]
        canceled_body = sub_canceled.json()
        assert canceled_body.get("status") == "canceled"
        assert canceled_body.get("cancelAtPeriodEnd") is True
        assert canceled_body.get("canCancel") is False

        checkout_resp = post_checkout_session(student_api, jwt, plan_id=plan_id)
        skip_if_checkout_unavailable(checkout_resp)
        assert checkout_resp.status_code == 409, (
            f"Expected 409 already_subscribed while canceled-in-period, got "
            f"{checkout_resp.status_code}: {checkout_resp.text[:200]}"
        )
        assert checkout_resp.json().get("code") == "already_subscribed"
    finally:
        _restore_active_subscription(
            api_base_url, user_sub, student_api, course_id, lesson_id, plan_id=plan_id
        )
