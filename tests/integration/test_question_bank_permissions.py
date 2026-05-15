"""HTTPS integration tests for question-bank and module-quiz create permissions (QB-B).

Canonical paths:

- ``POST /courses/{courseId}/question-banks`` — body ``{}`` optional
- ``POST /courses/{courseId}/modules/{moduleId}/quiz`` — body ``{}`` optional

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
    resp = api.create_module_quiz(course_id, module_id)
    assert resp.status_code == 201, resp.text


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
    resp = alt_api.create_module_quiz(course_id, module_id)
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
    resp = student_api.create_module_quiz(course_id, module_id)
    assert resp.status_code in (401, 403), f"Expected 401 or 403, got {resp.status_code}: {resp.text}"
    body = response_json_dict(resp)
    code = body.get("code")
    if code not in ("unauthorized", "forbidden"):
        pytest.fail(f"{EXPECTED_ROLE_DENIAL_JSON} status={resp.status_code} body={body!r}")
