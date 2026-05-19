"""HTTPS integration tests for question-bank module quiz visibility (QB-D slice 4).

``GET /courses/{courseId}/modules`` may include optional ``moduleQuiz`` when the course
is published, the viewer has lesson access (subscribed student or owner), and the linked
bank is published with ``served_count_n`` set.

See ``plans/question-banks-qb-d-plan.md`` and ``tests/integration/README.md``.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription
from helpers.factories import make_test_title
from helpers.module_contract import (
    EXPECTED_ROLE_DENIAL_JSON,
    require_course_modules_list,
    response_json_dict,
)

from test_question_bank_start import _publish_bank_and_course
from test_question_bank_submit import _answers_all_first_choice

_FORBIDDEN_JSON_KEYS = frozenset(
    {"questionBankId", "promptText", "correctOptionKey", "optionsJson"}
)
_ALLOWED_MODULE_QUIZ_KEYS = frozenset({"available", "servedCountN", "latestScorePercent"})


def _owner_draft_course_with_module(
    api: ApiClient, course_factory, *, label: str
) -> tuple[str, str]:
    course = course_factory(label=label)
    cr = api.create_course_module(
        course.course_id,
        title=make_test_title(f"{label}-mod"),
        description="",
    )
    assert cr.status_code == 201, cr.text
    module_id = str(cr.json()["moduleId"])
    return course.course_id, module_id


def _mcq_options() -> list[dict[str, str]]:
    return [
        {"key": "A", "text": "First choice"},
        {"key": "B", "text": "Second choice"},
    ]


def _setup_bank_quiz_and_drafts(
    api: ApiClient,
    course_id: str,
    module_id: str,
    *,
    draft_count: int = 2,
) -> str:
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text

    for i in range(draft_count):
        dr = api.create_draft_question(
            course_id,
            bank_id,
            prompt_text=f"Draft Q{i + 1}?",
            options_json=_mcq_options(),
            correct_option_key="A",
        )
        assert dr.status_code == 201, dr.text

    return bank_id


def _publish_course_with_ready_lesson(
    api: ApiClient,
    course_id: str,
    lesson_factory,
    *,
    label: str,
) -> str:
    """Publish course with one ready lesson; returns lesson_id."""
    lesson = lesson_factory(course_id, label=label)
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course_id, lesson.lesson_id).status_code == 200
    pr = api.publish_course(course_id)
    assert pr.status_code == 200, pr.text
    return lesson.lesson_id


def _subscribe_student(
    api_base_url: str, student_api: ApiClient, course_id: str, lesson_id: str
) -> None:
    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)


def _module_row(modules: list[dict[str, Any]], module_id: str) -> dict[str, Any]:
    row = next((m for m in modules if m.get("id") == module_id), None)
    assert row is not None, f"module {module_id!r} not in {modules!r}"
    return row


def _collect_json_keys(obj: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        keys.update(obj.keys())
        for value in obj.values():
            keys |= _collect_json_keys(value)
    elif isinstance(obj, list):
        for item in obj:
            keys |= _collect_json_keys(item)
    return keys


def _assert_no_module_list_leaks(modules: list[dict[str, Any]]) -> None:
    """Module list JSON must not expose bank or question fields (key-based, not substrings)."""
    leaked = _collect_json_keys(modules) & _FORBIDDEN_JSON_KEYS
    assert not leaked, f"leak scan: forbidden keys in module list JSON: {sorted(leaked)!r}"
    for row in modules:
        mq = row.get("moduleQuiz")
        if mq is None:
            continue
        extra = set(mq.keys()) - _ALLOWED_MODULE_QUIZ_KEYS
        assert not extra, f"moduleQuiz must only expose allowed keys; got extra {sorted(extra)!r}"


def test_draft_bank_hidden(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-vis-draft-hidden"
    )
    _setup_bank_quiz_and_drafts(api, course_id, module_id)

    lesson_id = _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-vis-draft-lesson"
    )
    _subscribe_student(api_base_url, student_api, course_id, lesson_id)

    modules = require_course_modules_list(student_api.list_course_modules(course_id))
    row = _module_row(modules, module_id)
    assert "moduleQuiz" not in row


def test_published_bank_visible(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-vis-published-visible"
    )
    bank_id = _setup_bank_quiz_and_drafts(api, course_id, module_id, draft_count=served_n)

    pub_bank = api.publish_question_bank(
        course_id, bank_id, n=served_n, module_id=module_id
    )
    assert pub_bank.status_code == 200, pub_bank.text

    lesson_id = _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-vis-pub-lesson"
    )
    _subscribe_student(api_base_url, student_api, course_id, lesson_id)

    modules = require_course_modules_list(student_api.list_course_modules(course_id))
    row = _module_row(modules, module_id)
    quiz = row.get("moduleQuiz")
    assert quiz is not None, f"expected moduleQuiz on {row!r}"
    assert quiz.get("available") is True
    assert quiz.get("servedCountN") == served_n


def test_owner_sees_module_quiz_without_enrollment(
    api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """Course publisher may see moduleQuiz via ownership without an enrollment row."""
    served_n = 2
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-vis-owner-no-enroll"
    )
    bank_id = _setup_bank_quiz_and_drafts(api, course_id, module_id, draft_count=served_n)

    pub_bank = api.publish_question_bank(
        course_id, bank_id, n=served_n, module_id=module_id
    )
    assert pub_bank.status_code == 200, pub_bank.text

    _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-vis-owner-lesson"
    )

    modules = require_course_modules_list(api.list_course_modules(course_id))
    row = _module_row(modules, module_id)
    quiz = row.get("moduleQuiz")
    assert quiz is not None, f"expected moduleQuiz for owner on {row!r}"
    assert quiz.get("available") is True
    assert quiz.get("servedCountN") == served_n


def test_unenrolled_no_quiz(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 1
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-vis-unenrolled"
    )
    bank_id = _setup_bank_quiz_and_drafts(api, course_id, module_id, draft_count=served_n)

    pub_bank = api.publish_question_bank(
        course_id, bank_id, n=served_n, module_id=module_id
    )
    assert pub_bank.status_code == 200, pub_bank.text

    _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-vis-unenroll-lesson"
    )

    modules = require_course_modules_list(student_api.list_course_modules(course_id))
    for row in modules:
        assert "moduleQuiz" not in row, f"unenrolled viewer must not see quiz on {row!r}"


def _score_percent_from_counts(*, correct_count: int, total_count: int) -> int:
    return (correct_count * 100 + total_count // 2) // total_count


def test_module_list_includes_latest_score_percent_after_submit(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id, _ = _publish_bank_and_course(
        api_base_url,
        api,
        student_api,
        course_factory,
        lesson_factory,
        label="qb-vis-latest-score",
        served_n=served_n,
    )

    modules_before = require_course_modules_list(student_api.list_course_modules(course_id))
    quiz_before = _module_row(modules_before, module_id).get("moduleQuiz")
    assert quiz_before is not None
    assert quiz_before.get("latestScorePercent") is None

    start = student_api.start_module_quiz(course_id, module_id)
    assert start.status_code == 200, start.text
    start_body = response_json_dict(start)
    attempt_id = str(start_body["attemptId"])
    answers = _answers_all_first_choice(start_body)

    sub = student_api.submit_module_quiz(
        course_id,
        module_id,
        {"attemptId": attempt_id, "answers": answers},
    )
    assert sub.status_code == 200, sub.text
    sub_body = response_json_dict(sub)
    correct_count = int(sub_body["correctCount"])
    total_count = int(sub_body["totalCount"])
    expected_pct = _score_percent_from_counts(
        correct_count=correct_count, total_count=total_count
    )

    modules_after = require_course_modules_list(student_api.list_course_modules(course_id))
    quiz_after = _module_row(modules_after, module_id).get("moduleQuiz")
    assert quiz_after is not None
    assert quiz_after.get("latestScorePercent") == expected_pct


def test_leak_scan(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-vis-leak-scan"
    )
    bank_id = _setup_bank_quiz_and_drafts(api, course_id, module_id, draft_count=served_n)

    pub_bank = api.publish_question_bank(
        course_id, bank_id, n=served_n, module_id=module_id
    )
    assert pub_bank.status_code == 200, pub_bank.text

    lesson_id = _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-vis-leak-lesson"
    )
    _subscribe_student(api_base_url, student_api, course_id, lesson_id)

    resp = student_api.list_course_modules(course_id)
    assert resp.status_code == 200, resp.text
    modules = resp.json()
    assert isinstance(modules, list)
    _assert_no_module_list_leaks(modules)
    row = _module_row(modules, module_id)
    assert row.get("moduleQuiz", {}).get("available") is True


def test_student_cannot_publish(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 1
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-vis-student-publish"
    )
    bank_id = _setup_bank_quiz_and_drafts(api, course_id, module_id, draft_count=served_n)

    lesson_id = _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-vis-student-pub-lesson"
    )
    _subscribe_student(api_base_url, student_api, course_id, lesson_id)

    pr = student_api.publish_question_bank(
        course_id, bank_id, n=served_n, module_id=module_id
    )
    assert pr.status_code in (401, 403), f"Expected 401 or 403, got {pr.status_code}: {pr.text}"
    body = response_json_dict(pr)
    if body.get("code") not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={pr.status_code} body={body!r}")
