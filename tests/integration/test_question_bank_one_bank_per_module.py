"""HTTPS integration: one question bank per module (409 when re-attaching same bank)."""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import response_json_dict


def _owner_draft_course_with_two_modules(
    api: ApiClient, course_factory, *, label: str
) -> tuple[str, str, str]:
    course = course_factory(label=label)
    cr_a = api.create_course_module(
        course.course_id,
        title=make_test_title(f"{label}-mod-a"),
        description="",
    )
    assert cr_a.status_code == 201, cr_a.text
    module_a_id = str(cr_a.json()["moduleId"])
    cr_b = api.create_course_module(
        course.course_id,
        title=make_test_title(f"{label}-mod-b"),
        description="",
    )
    assert cr_b.status_code == 201, cr_b.text
    module_b_id = str(cr_b.json()["moduleId"])
    return course.course_id, module_a_id, module_b_id


def test_owner_cannot_attach_same_bank_to_second_module_returns_409(
    api: ApiClient, course_factory
) -> None:
    course_id, module_a_id, module_b_id = _owner_draft_course_with_two_modules(
        api, course_factory, label="qb-one-bank-per-module"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    first = api.create_module_quiz(
        course_id, module_a_id, question_bank_id=bank_id
    )
    assert first.status_code == 201, first.text

    second = api.create_module_quiz(
        course_id, module_b_id, question_bank_id=bank_id
    )
    assert second.status_code == 409, (
        f"Expected 409 when reusing bank on second module, got {second.status_code}: "
        f"{second.text}"
    )
    body = response_json_dict(second)
    assert body.get("code") == "conflict"
    message = str(body.get("message", "")).lower()
    assert "bank" in message and "linked" in message, body
