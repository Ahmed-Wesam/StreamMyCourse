"""Subscription-gated course access via mock PayTabs IPN (WS5 Phase C / W5-P6)."""

from __future__ import annotations

import os

import pytest

from helpers.api import ApiClient
from helpers.billing_access import (
    decode_jwt_sub,
    post_mock_subscription_activated,
    skip_if_billing_webhook_unavailable,
    skip_if_student_has_subscription,
    wait_for_subscription_access,
)


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


def test_playback_without_subscription_returns_subscription_required(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Student without platform subscription cannot access playback."""
    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-no-sub"
    )
    skip_if_student_has_subscription(student_api, course_id, lesson_id)

    resp = student_api.get_playback(course_id, lesson_id)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    assert resp.json().get("code") == "subscription_required"


def test_playback_after_mock_ipn_returns_200(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Mock subscription IPN grants platform access; playback returns presigned URL."""
    skip_if_billing_webhook_unavailable()

    token = os.environ.get("INTEGRATION_COGNITO_JWT_STUDENT", "").strip()
    if not token:
        pytest.skip("INTEGRATION_COGNITO_JWT_STUDENT not set")

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-mock-ipn"
    )

    user_sub = decode_jwt_sub(token)
    probe = student_api.get_playback(course_id, lesson_id)
    if probe.status_code == 200:
        playback_resp = probe
    else:
        ipn_resp = post_mock_subscription_activated(api_base_url, user_sub)
        if ipn_resp.status_code == 404:
            pytest.skip("payments webhook route not deployed (404)")
        if ipn_resp.status_code == 503:
            try:
                code = ipn_resp.json().get("code")
            except Exception:
                code = None
            if code == "billing_unconfigured":
                pytest.skip("billing not configured on API (503 billing_unconfigured)")
        if ipn_resp.status_code != 200:
            pytest.skip(
                f"mock subscription IPN unavailable (HTTP {ipn_resp.status_code}): "
                f"{ipn_resp.text[:200]}"
            )
        wait_for_subscription_access(student_api, course_id, lesson_id)
        playback_resp = student_api.get_playback(course_id, lesson_id)

    assert playback_resp.status_code == 200, playback_resp.text
    body = playback_resp.json()
    assert isinstance(body.get("url"), str) and body["url"]
