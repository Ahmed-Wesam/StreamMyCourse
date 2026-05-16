"""HTTPS integration tests for question-bank and module-quiz create permissions (QB-B).

Canonical paths:

- ``POST /courses/{courseId}/question-banks`` — body requires ``name``
- ``PATCH /courses/{courseId}/question-banks/{questionBankId}`` — body requires ``name``
- ``POST /courses/{courseId}/modules/{moduleId}/quiz`` — body must include ``questionBankId`` (400 ``bad_request`` when missing)

**Successful create:** **201 Created** (same convention as ``create_course_module``).

**Denials:** non-owner teacher **403** with ``code: forbidden``; student **401** or **403**
with ``code`` in ``unauthorized`` / ``forbidden`` (see ``helpers.module_contract``).

See ``tests/integration/README.md`` for required env (JWTs, API base URL).
"""

from __future__ import annotations

import pytest

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import (
    EXPECTED_CATALOG_FORBIDDEN_403,
    EXPECTED_ROLE_DENIAL_JSON,
    require_lambda_json_or_skip,
    response_json_dict,
)


def _owner_draft_course_with_module(
    api: ApiClient, course_factory, *, label: str
) -> tuple[str, str]:
    """Owner draft course plus at least one module via ``create_course_module`` (integration pattern)."""
    course = course_factory(label=label)
    cr = api.create_course_module(
        course.course_id,
        title=make_test_title(f"{label}-mod"),
        description="",
    )
    assert cr.status_code == 201, cr.text
    module_id = str(cr.json()["moduleId"])
    return course.course_id, module_id


def _qb_patch_options() -> list[dict[str, str]]:
    return [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}]


def _draft_bank_with_question_ids(
    api: ApiClient, course_factory, *, label: str
) -> tuple[str, str, str]:
    course_id, _mid = _owner_draft_course_with_module(api, course_factory, label=label)
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="perm-q?",
        options_json=_qb_patch_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 201, dr.text
    return course_id, bank_id, str(dr.json()["questionId"])


def test_owner_can_create_question_bank(api: ApiClient, course_factory) -> None:
    course_id, _module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-perm-owner-bank"
    )
    resp = api.create_question_bank(course_id)
    assert resp.status_code == 201, resp.text


def test_owner_can_create_module_quiz(api: ApiClient, course_factory) -> None:
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-perm-owner-quiz"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    resp = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert resp.status_code == 201, resp.text


def test_owner_post_module_quiz_without_question_bank_id_returns_400(
    api: ApiClient, course_factory
) -> None:
    """``POST .../quiz`` without ``questionBankId`` returns 400 ``bad_request``."""
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-perm-owner-quiz-no-bank"
    )
    resp = api.create_module_quiz(course_id, module_id)
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    assert body.get("code") == "bad_request"


def test_alt_teacher_cannot_create_question_bank(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    """Alternate teacher (fixture ``alt_api``) must not create banks on another teacher's course."""
    course_id, _mid = _owner_draft_course_with_module(api, course_factory, label="qb-perm-alt-bank")
    resp = alt_api.create_question_bank(course_id)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_alt_teacher_cannot_rename_question_bank(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    """Rename keeps the same publisher/admin scope as bank create."""
    course_id, _mid = _owner_draft_course_with_module(
        api, course_factory, label="qb-perm-alt-rename"
    )
    br = api.create_question_bank(course_id, name="Owner bank")
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    resp = alt_api.rename_question_bank(course_id, bank_id, name="Alt rename")
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_student_cannot_create_question_bank(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    """Student principal cannot call instructor-only create (same bar as ``test_student_permissions_denials``)."""
    course_id, _mid = _owner_draft_course_with_module(api, course_factory, label="qb-perm-student-bank")
    resp = student_api.create_question_bank(course_id)
    assert resp.status_code in (401, 403), f"Expected 401 or 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    code = body.get("code")
    if code not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={resp.status_code} body={body!r}")


def test_alt_teacher_cannot_create_module_quiz(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    """Alternate teacher must not create module quiz rows on another teacher's course."""
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-perm-alt-quiz"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    resp = alt_api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_student_cannot_create_module_quiz(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    """Student must not call instructor-only module quiz create."""
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-perm-student-quiz"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    resp = student_api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert resp.status_code in (401, 403), f"Expected 401 or 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    code = body.get("code")
    if code not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={resp.status_code} body={body!r}")


def test_alt_teacher_cannot_patch_draft_question(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    course_id, bank_id, qid = _draft_bank_with_question_ids(
        api, course_factory, label="qb-perm-alt-patch"
    )
    resp = alt_api.patch_question(course_id, bank_id, qid, body={"promptText": "nope"})
    body = require_lambda_json_or_skip(resp, hint="PATCH question alt teacher")
    assert resp.status_code == 403, resp.text
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_student_cannot_patch_draft_question(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    course_id, bank_id, qid = _draft_bank_with_question_ids(
        api, course_factory, label="qb-perm-student-patch"
    )
    resp = student_api.patch_question(course_id, bank_id, qid, body={"promptText": "nope"})
    body = require_lambda_json_or_skip(resp, hint="PATCH question student")
    assert resp.status_code in (401, 403), resp.text
    code = body.get("code")
    if code not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={resp.status_code} body={body!r}")


def test_alt_teacher_cannot_delete_draft_question(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    course_id, bank_id, qid = _draft_bank_with_question_ids(
        api, course_factory, label="qb-perm-alt-del-q"
    )
    resp = alt_api.delete_question_bank_question(course_id, bank_id, qid)
    body = require_lambda_json_or_skip(resp, hint="DELETE question alt teacher")
    assert resp.status_code == 403, resp.text
    if body.get("code") != "forbidden":
        pytest.fail(f"{EXPECTED_CATALOG_FORBIDDEN_403} Got: {body!r}")


def test_student_cannot_delete_draft_question(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    course_id, bank_id, qid = _draft_bank_with_question_ids(
        api, course_factory, label="qb-perm-student-del-q"
    )
    resp = student_api.delete_question_bank_question(course_id, bank_id, qid)
    body = require_lambda_json_or_skip(resp, hint="DELETE question student")
    assert resp.status_code in (401, 403), resp.text
    code = body.get("code")
    if code not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={resp.status_code} body={body!r}")
