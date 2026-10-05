"""Purchase-gated course access via checkout + HyperPay webhook (RS-5)."""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.billing_access import (
    ensure_student_subscription,
    skip_if_billing_webhook_unavailable,
    skip_if_student_has_subscription,
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
    assert resp.json().get("code") == "purchase_required"


def test_playback_after_mock_ipn_returns_200(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Mock subscription IPN grants platform access; playback returns presigned URL."""
    skip_if_billing_webhook_unavailable()

    course_id, lesson_id = _publish_course_with_lesson(
        api, course_factory, lesson_factory, label="billing-mock-ipn"
    )

    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)
    playback_resp = student_api.get_playback(course_id, lesson_id)

    assert playback_resp.status_code == 200, playback_resp.text
    from helpers.playback_contract import assert_playback_contract

    assert_playback_contract(playback_resp.json())
