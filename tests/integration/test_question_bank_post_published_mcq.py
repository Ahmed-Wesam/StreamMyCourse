"""HTTPS integration tests for POST .../question-banks/{bid}/questions on PUBLISHED banks (QB-K slice B).

Same path as draft create; published banks accept full MCQ with required ``correctOptionKey``.
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
        {"key": "A", "text": "First"},
        {"key": "B", "text": "Second"},
    ]


@pytest.fixture
def published_bank_ids(
    api: ApiClient, course_factory
) -> tuple[str, str]:
    """Course id + bank id after publish (one draft promoted)."""
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-k-post-pub"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text
    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Seed?",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 201, dr.text
    pr = api.publish_question_bank(course_id, bank_id, n=1, module_id=module_id)
    assert pr.status_code == 200, pr.text
    return course_id, bank_id


def test_owner_post_mcq_on_published_bank_ok(
    api: ApiClient, published_bank_ids: tuple[str, str]
) -> None:
    course_id, bank_id = published_bank_ids
    resp = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="After publish?",
        options_json=_mcq_options(),
        correct_option_key="B",
    )
    assert resp.status_code == 201, resp.text
    body = response_json_dict(resp)
    assert "questionId" in body
    assert str(body["questionId"])


def test_post_published_bank_without_correct_key_returns_400(
    api: ApiClient, published_bank_ids: tuple[str, str]
) -> None:
    course_id, bank_id = published_bank_ids
    resp = api.raw.post(
        f"/courses/{course_id}/question-banks/{bank_id}/questions",
        json={
            "promptText": "No correct key",
            "optionsJson": _mcq_options(),
        },
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    err = response_json_dict(resp)
    assert err.get("code") == "bad_request"


def test_alt_teacher_cannot_post_mcq_on_owner_published_bank(
    api: ApiClient,
    alt_api: ApiClient,
    published_bank_ids: tuple[str, str],
) -> None:
    course_id, bank_id = published_bank_ids
    resp = alt_api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Intruder published add",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_student_cannot_post_mcq_on_published_bank(
    api: ApiClient,
    student_api: ApiClient,
    published_bank_ids: tuple[str, str],
) -> None:
    course_id, bank_id = published_bank_ids
    resp = student_api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Student add",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert resp.status_code in (401, 403), (
        f"Expected 401 or 403, got {resp.status_code}: {resp.text}"
    )
    body = response_json_dict(resp)
    if body.get("code") not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={resp.status_code} body={body!r}")
