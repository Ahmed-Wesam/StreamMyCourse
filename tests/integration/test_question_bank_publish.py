"""HTTPS integration tests for question-bank draft questions and publish (QB slice 5).

Paths:

- ``POST /courses/{courseId}/question-banks/{questionBankId}/questions``
- ``POST /courses/{courseId}/question-banks/{questionBankId}/publish``

Publishing requires a ``module_quizzes`` row for ``moduleId`` with matching ``question_bank_id``.
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import (
    EXPECTED_CATALOG_FORBIDDEN_403,
    EXPECTED_ROLE_DENIAL_JSON,
    response_json_dict,
)


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


def test_owner_publish_happy_path(api: ApiClient, course_factory) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-pub-owner-happy"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text

    for i in range(2):
        dr = api.create_draft_question(
            course_id,
            bank_id,
            prompt_text=f"Q{i + 1}?",
            options_json=_mcq_options(),
            correct_option_key="A",
        )
        assert dr.status_code == 201, dr.text
        assert "questionId" in dr.json()

    pr = api.publish_question_bank(course_id, bank_id, n=2, module_id=module_id)
    assert pr.status_code == 200, pr.text
    body = response_json_dict(pr)
    assert body.get("status") == "PUBLISHED"


def test_publish_n_greater_than_draft_count_returns_400(
    api: ApiClient, course_factory
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-pub-n-too-large"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text

    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Only one?",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 201, dr.text

    pr = api.publish_question_bank(course_id, bank_id, n=2, module_id=module_id)
    assert pr.status_code == 400, f"Expected 400, got {pr.status_code}: {pr.text}"
    err = response_json_dict(pr)
    assert err.get("code") == "bad_request"


def test_alt_teacher_cannot_publish_owner_bank(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-pub-alt-publish"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text
    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Alt publish denial",
        options_json=_mcq_options(),
        correct_option_key="B",
    )
    assert dr.status_code == 201, dr.text

    pr = alt_api.publish_question_bank(course_id, bank_id, n=1, module_id=module_id)
    assert pr.status_code == 403, f"Expected 403, got {pr.status_code}: {pr.text}"
    body = response_json_dict(pr)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_alt_teacher_cannot_create_draft_on_owner_bank(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-pub-alt-draft"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text

    dr = alt_api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Intruder draft",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 403, f"Expected 403, got {dr.status_code}: {dr.text}"
    body = response_json_dict(dr)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_publish_without_linked_module_quiz_returns_400(
    api: ApiClient, course_factory
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-pub-no-quiz-link"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Orphan bank",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 201, dr.text

    pr = api.publish_question_bank(course_id, bank_id, n=1, module_id=module_id)
    assert pr.status_code == 400, f"Expected 400, got {pr.status_code}: {pr.text}"
    err = response_json_dict(pr)
    assert err.get("code") == "bad_request"


def test_publish_twice_returns_conflict(
    api: ApiClient, course_factory
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-pub-twice"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text

    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Once?",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 201, dr.text

    pr1 = api.publish_question_bank(course_id, bank_id, n=1, module_id=module_id)
    assert pr1.status_code == 200, pr1.text

    pr2 = api.publish_question_bank(course_id, bank_id, n=1, module_id=module_id)
    assert pr2.status_code == 409, f"Expected 409, got {pr2.status_code}: {pr2.text}"
    err = response_json_dict(pr2)
    assert err.get("code") == "conflict"


def test_student_cannot_publish_or_create_draft(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-pub-student"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text
    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Student denial setup",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 201, dr.text

    pr = student_api.publish_question_bank(course_id, bank_id, n=1, module_id=module_id)
    assert pr.status_code in (401, 403), f"Expected 401 or 403, got {pr.status_code}: {pr.text}"
    body_p = response_json_dict(pr)
    if body_p.get("code") not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={pr.status_code} body={body_p!r}")

    dr2 = student_api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Student draft",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert dr2.status_code in (401, 403), f"Expected 401 or 403, got {dr2.status_code}: {dr2.text}"
    body_d = response_json_dict(dr2)
    if body_d.get("code") not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={dr2.status_code} body={body_d!r}")
