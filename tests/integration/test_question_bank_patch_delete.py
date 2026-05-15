"""HTTPS integration tests for PATCH/DELETE question-bank questions (QB-K slice C).

Until ``PATCH``/``DELETE`` on ``.../question-banks/{bid}/questions/{qid}`` is deployed
(**CatalogApiDeploymentV24** + catalog Lambda), API Gateway often responds with **403**
(non-JSON "Missing Authentication Token") or **404** — those runs **skip** via
``require_lambda_json_or_skip`` because the request never reaches the catalog Lambda.
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import require_lambda_json_or_skip


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
def published_bank_with_promoted_question(
    api: ApiClient, course_factory
) -> tuple[str, str, str]:
    """Course id, bank id, and the question id that becomes **PUBLISHED** after publish (n=1)."""
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-k-patch-pub"
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
    promoted_qid = str(dr.json()["questionId"])
    pr = api.publish_question_bank(course_id, bank_id, n=1, module_id=module_id)
    assert pr.status_code == 200, pr.text
    return course_id, bank_id, promoted_qid


@pytest.fixture
def draft_bank_with_question(
    api: ApiClient, course_factory
) -> tuple[str, str, str]:
    course_id, _module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-k-patch-draft"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Draft line?",
        options_json=_mcq_options(),
        correct_option_key="B",
    )
    assert dr.status_code == 201, dr.text
    q_id = str(dr.json()["questionId"])
    return course_id, bank_id, q_id


def test_patch_published_question_returns_conflict(
    api: ApiClient,
    published_bank_with_promoted_question: tuple[str, str, str],
) -> None:
    course_id, bank_id, qid = published_bank_with_promoted_question
    resp = api.patch_question(
        course_id,
        bank_id,
        qid,
        body={"promptText": "Try mutate published"},
    )
    body = require_lambda_json_or_skip(resp, hint="PATCH published bank question")
    assert resp.status_code == 409, resp.text
    assert body.get("code") == "conflict"


def test_delete_published_question_returns_conflict(
    api: ApiClient,
    published_bank_with_promoted_question: tuple[str, str, str],
) -> None:
    course_id, bank_id, qid = published_bank_with_promoted_question
    post_add = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="Extra published?",
        options_json=_mcq_options(),
        correct_option_key="A",
    )
    assert post_add.status_code == 201, post_add.text
    extra_qid = str(post_add.json()["questionId"])
    resp = api.delete_question_bank_question(course_id, bank_id, extra_qid)
    body = require_lambda_json_or_skip(resp, hint="DELETE published bank question")
    assert resp.status_code == 409, resp.text
    assert body.get("code") == "conflict"


def test_patch_draft_question_ok(
    api: ApiClient,
    draft_bank_with_question: tuple[str, str, str],
) -> None:
    course_id, bank_id, qid = draft_bank_with_question
    resp = api.patch_question(
        course_id,
        bank_id,
        qid,
        body={"promptText": "Patched prompt"},
    )
    body = require_lambda_json_or_skip(resp, hint="PATCH draft question")
    assert resp.status_code == 200, resp.text
    assert body.get("status") == "updated"


def test_delete_draft_question_ok(
    api: ApiClient,
    draft_bank_with_question: tuple[str, str, str],
) -> None:
    course_id, bank_id, qid = draft_bank_with_question
    resp = api.delete_question_bank_question(course_id, bank_id, qid)
    body = require_lambda_json_or_skip(resp, hint="DELETE draft question")
    assert resp.status_code == 200, resp.text
    assert body.get("status") == "deleted"


def test_patch_wrong_question_id_returns_not_found(
    api: ApiClient,
    published_bank_with_promoted_question: tuple[str, str, str],
) -> None:
    course_id, bank_id, _promoted = published_bank_with_promoted_question
    wrong_qid = "00000000-0000-4000-8000-000000000001"
    resp = api.patch_question(
        course_id,
        bank_id,
        wrong_qid,
        body={"promptText": "nope"},
    )
    body = require_lambda_json_or_skip(resp, hint="PATCH wrong question id")
    assert resp.status_code == 404, resp.text
    assert body.get("code") == "not_found"
