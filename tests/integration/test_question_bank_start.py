"""HTTPS integration tests for ``POST .../modules/{moduleId}/quiz/start`` (QB-F slice 5).

Student binding draw, idempotent reload, 404 gates (unenrolled, unpublished bank),
IDOR on path ``courseId``, and publisher-route denial for students.

See ``plans/question-banks-qb-f-plan.md`` and ``tests/integration/README.md``.
"""

from __future__ import annotations

from typing import Any

import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import (
    EXPECTED_CATALOG_FORBIDDEN_403,
    response_json_dict,
)

_FORBIDDEN_START_JSON_KEYS = frozenset(
    {"questionBankId", "correctOptionKey", "status"}
)
_START_QUESTION_ALLOWED_KEYS = frozenset({"id", "promptText", "optionsJson"})


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
) -> None:
    lesson = lesson_factory(course_id, label=label)
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course_id, lesson.lesson_id).status_code == 200
    pr = api.publish_course(course_id)
    assert pr.status_code == 200, pr.text


def _enroll_student(student_api: ApiClient, course_id: str) -> None:
    enroll_resp = student_api.enroll_course(course_id)
    assert enroll_resp.status_code in (200, 201), enroll_resp.text


def _publish_bank_and_course(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
    *,
    label: str,
    served_n: int = 2,
) -> tuple[str, str]:
    """Owner setup: bank + drafts + publish bank + publish course + enroll student."""
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label=label
    )
    bank_id = _setup_bank_quiz_and_drafts(
        api, course_id, module_id, draft_count=served_n
    )
    pub_bank = api.publish_question_bank(
        course_id, bank_id, n=served_n, module_id=module_id
    )
    assert pub_bank.status_code == 200, pub_bank.text
    _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label=f"{label}-lesson"
    )
    _enroll_student(student_api, course_id)
    return course_id, module_id


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


def _assert_no_start_response_leaks(body: dict[str, Any]) -> None:
    leaked = _collect_json_keys(body) & _FORBIDDEN_START_JSON_KEYS
    assert not leaked, f"leak scan: forbidden keys in start JSON: {sorted(leaked)!r}"
    dumped = str(body)
    assert "DRAFT" not in dumped, "leak scan: DRAFT must not appear in start response body"
    for question in body.get("questions") or []:
        assert isinstance(question, dict), f"expected question object, got {question!r}"
        extra = set(question.keys()) - _START_QUESTION_ALLOWED_KEYS
        assert not extra, f"question must only expose student-safe keys; got extra {sorted(extra)!r}"


def _question_ids_from_start(body: dict[str, Any]) -> list[str]:
    questions = body.get("questions")
    assert isinstance(questions, list), f"expected questions array in {body!r}"
    return [str(q["id"]) for q in questions]


def test_enrolled_student_start_returns_bound_questions(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id = _publish_bank_and_course(
        api,
        student_api,
        course_factory,
        lesson_factory,
        label="qb-start-happy",
        served_n=served_n,
    )

    resp = student_api.start_module_quiz(course_id, module_id)
    assert resp.status_code == 200, resp.text
    body = response_json_dict(resp)
    assert body.get("moduleId") == module_id
    assert body.get("servedCountN") == served_n
    questions = body.get("questions")
    assert isinstance(questions, list)
    assert len(questions) == served_n
    _assert_no_start_response_leaks(body)


def test_second_start_returns_same_question_ids(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id = _publish_bank_and_course(
        api,
        student_api,
        course_factory,
        lesson_factory,
        label="qb-start-idempotent",
        served_n=served_n,
    )

    first = student_api.start_module_quiz(course_id, module_id)
    assert first.status_code == 200, first.text
    first_ids = _question_ids_from_start(response_json_dict(first))

    second = student_api.start_module_quiz(course_id, module_id)
    assert second.status_code == 200, second.text
    second_ids = _question_ids_from_start(response_json_dict(second))

    assert second_ids == first_ids


def test_unenrolled_student_start_returns_404(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    served_n = 2
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-start-unenrolled"
    )
    bank_id = _setup_bank_quiz_and_drafts(api, course_id, module_id, draft_count=served_n)
    pub_bank = api.publish_question_bank(
        course_id, bank_id, n=served_n, module_id=module_id
    )
    assert pub_bank.status_code == 200, pub_bank.text
    _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-start-unenroll-lesson"
    )

    resp = student_api.start_module_quiz(course_id, module_id)
    assert resp.status_code == 404, resp.text
    body = response_json_dict(resp)
    assert body.get("code") == "not_found"


def test_start_before_bank_publish_returns_404(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-start-draft-bank"
    )
    _setup_bank_quiz_and_drafts(api, course_id, module_id, draft_count=2)
    _publish_course_with_ready_lesson(
        api, course_id, lesson_factory, label="qb-start-draft-bank-lesson"
    )
    _enroll_student(student_api, course_id)

    resp = student_api.start_module_quiz(course_id, module_id)
    assert resp.status_code == 404, resp.text
    body = response_json_dict(resp)
    assert body.get("code") == "not_found"


def test_start_wrong_course_id_returns_404(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """IDOR: valid moduleId from course A must not start under course B path."""
    served_n = 2
    course_a_id, module_a_id = _publish_bank_and_course(
        api,
        student_api,
        course_factory,
        lesson_factory,
        label="qb-start-idor-a",
        served_n=served_n,
    )
    course_b = course_factory(label="qb-start-idor-b")
    course_b_id = course_b.course_id

    resp = student_api.start_module_quiz(course_b_id, module_a_id)
    assert resp.status_code == 404, (
        f"wrong courseId in path must not expose module from {course_a_id!r}; "
        f"got {resp.status_code}: {resp.text}"
    )
    body = response_json_dict(resp)
    assert body.get("code") == "not_found"


def test_student_cannot_create_question_bank(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
) -> None:
    course_id, _module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-start-student-bank"
    )
    resp = student_api.create_question_bank(course_id)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")
