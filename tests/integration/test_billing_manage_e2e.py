"""Subscription manage E2E: cancel at period end → reactivate (WS7 W7-P10)."""

from __future__ import annotations

import os

import pytest

from helpers.api import ApiClient
from helpers.billing_access import (
    decode_jwt_sub,
    ensure_student_subscription,
    get_subscription,
    post_cancel_subscription,
    post_checkout_session,
    post_mock_subscription_activated,
    post_mock_subscription_renewed,
    post_reactivate_subscription,
    seed_plan_id,
    skip_if_billing_webhook_unavailable,
    skip_if_checkout_unavailable,
    skip_if_manage_read_unavailable,
    skip_if_mock_ipn_unavailable,
    wait_for_subscription_access,
)


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


def test_cancel_at_period_end_then_reactivate_single_row(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Mock IPN → manage cancel/reactivate; playback and checkout gates unchanged."""
    skip_if_billing_webhook_unavailable()
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
        assert cancel_resp.status_code == 200, cancel_resp.text[:200]
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
        assert canceled_body.get("canReactivate") is True
        assert canceled_body.get("canCancel") is False

        react_resp = post_reactivate_subscription(student_api)
        skip_if_checkout_unavailable(react_resp)
        assert react_resp.status_code == 200, react_resp.text[:200]
        react_body = react_resp.json()
        assert react_body.get("status") == "active"
        assert react_body.get("cancelAtPeriodEnd") is False

        sub_active = get_subscription(student_api)
        skip_if_manage_read_unavailable(sub_active)
        assert sub_active.status_code == 200, sub_active.text[:200]
        assert sub_active.json().get("status") == "active"
        assert sub_active.json().get("canCancel") is True

        checkout_resp = post_checkout_session(student_api, jwt, plan_id=plan_id)
        skip_if_checkout_unavailable(checkout_resp)
        assert checkout_resp.status_code == 409, (
            f"Expected 409 already_subscribed, got {checkout_resp.status_code}: "
            f"{checkout_resp.text[:200]}"
        )
        assert checkout_resp.json().get("code") == "already_subscribed"
    finally:
        _restore_active_subscription(
            api_base_url, user_sub, student_api, course_id, lesson_id, plan_id=plan_id
        )


def test_renewal_ipn_after_cancel_preserves_canceled_in_period(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """W7-P3c: mock renewal IPN must not clobber cancel-at-period-end row."""
    skip_if_billing_webhook_unavailable()
    jwt = _student_jwt_or_skip()
    user_sub = decode_jwt_sub(jwt)
    plan_id = seed_plan_id()

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-manage-renewal-guard"
    )

    try:
        ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)

        cancel_resp = post_cancel_subscription(student_api)
        skip_if_checkout_unavailable(cancel_resp)
        assert cancel_resp.status_code == 200, cancel_resp.text[:200]
        assert cancel_resp.json().get("cancelAtPeriodEnd") is True

        renewal_resp = post_mock_subscription_renewed(
            api_base_url, user_sub, plan_id=plan_id
        )
        skip_if_mock_ipn_unavailable(renewal_resp)

        sub_resp = get_subscription(student_api)
        skip_if_manage_read_unavailable(sub_resp)
        assert sub_resp.status_code == 200, sub_resp.text[:200]
        body = sub_resp.json()
        assert body.get("status") == "canceled", body
        assert body.get("cancelAtPeriodEnd") is True
        assert body.get("canReactivate") is True

        playback_resp = student_api.get_playback(course_id, lesson_id)
        assert playback_resp.status_code == 200, playback_resp.text[:200]
    finally:
        react_resp = post_reactivate_subscription(student_api)
        if react_resp.status_code != 200:
            _restore_active_subscription(
                api_base_url, user_sub, student_api, course_id, lesson_id, plan_id=plan_id
            )
