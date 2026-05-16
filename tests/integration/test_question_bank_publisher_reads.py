"""HTTPS integration tests for publisher question-bank reads (QB-L Plan 1 + Plan 2).

Covers GET ``/courses/{courseId}/question-banks`` and
GET ``/courses/{courseId}/question-banks/{questionBankId}/questions`` with
draft visibility parity against ``GET /courses/{id}/modules`` (and lessons).

Plan 2 adds GET ``/courses/{courseId}/module-quizzes`` (publisher module-quiz rows).

See ``tests/integration/README.md`` for required env (JWTs, API base URL).
"""

from __future__ import annotations

import uuid

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import response_json_dict


def _qb_patch_options() -> list[dict[str, str]]:
    return [{"key": "A", "text": "a"}, {"key": "B", "text": "b"}]


def _owner_draft_course_with_module(
    api: ApiClient, course_factory, *, label: str
) -> tuple[str, str]:
    """Owner draft course plus at least one module (same pattern as ``test_question_bank_permissions``)."""
    course = course_factory(label=label)
    cr = api.create_course_module(
        course.course_id,
        title=make_test_title(f"{label}-mod"),
        description="",
    )
    assert cr.status_code == 201, cr.text
    module_id = str(cr.json()["moduleId"])
    return course.course_id, module_id


def _draft_bank_with_one_question(
    api: ApiClient, course_factory, *, label: str
) -> tuple[str, str, str]:
    """Owner course with one bank and one draft question."""
    course_id, _mid = _owner_draft_course_with_module(api, course_factory, label=label)
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    dr = api.create_draft_question(
        course_id,
        bank_id,
        prompt_text="read-q?",
        options_json=_qb_patch_options(),
        correct_option_key="A",
    )
    assert dr.status_code == 201, dr.text
    return course_id, bank_id, str(dr.json()["questionId"])


def test_owner_lists_empty_question_banks(api: ApiClient, course_factory) -> None:
    """No banks yet → 200 and JSON list ``[]``."""
    course = course_factory(label="qb-read-empty-banks")
    resp = api.list_question_banks(course.course_id)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list), f"Expected JSON list, got {type(data).__name__}: {data!r}"
    assert data == []


def test_owner_lists_empty_module_quizzes(api: ApiClient, course_factory) -> None:
    """Owner draft course, no ``module_quiz`` rows → **200** and JSON list ``[]`` (contract).

    Until ``GET /courses/{courseId}/module-quizzes`` is handled by the question-banks
    controller (QB-L Plan 2 green slice), the request may fall through to the catalog
    ``not_found`` path (**404** + ``code`` ``not_found``) or, if API Gateway has no
    route to Lambda, **403** with a non-catalog body. This test asserts the eventual
    success contract and stays **RED** until routing + handler return **200** + ``[]``.
    """
    course = course_factory(label="qb-read-empty-module-quizzes")
    resp = api.list_module_quizzes(course.course_id)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list), f"Expected JSON list, got {type(data).__name__}: {data!r}"
    assert data == []


def test_owner_lists_bank_and_draft_question_shapes(
    api: ApiClient, course_factory
) -> None:
    course_id, bank_id, _qid = _draft_bank_with_one_question(
        api, course_factory, label="qb-read-owner-shapes"
    )

    banks_r = api.list_question_banks(course_id)
    assert banks_r.status_code == 200, banks_r.text
    banks_body = banks_r.json()
    assert isinstance(banks_body, list), banks_body
    assert len(banks_body) >= 1
    bank_row = next((b for b in banks_body if str(b.get("questionBankId")) == bank_id), None)
    assert bank_row is not None, f"bank {bank_id} not in list: {banks_body!r}"
    for key in ("questionBankId", "status", "createdAt", "updatedAt"):
        assert key in bank_row, f"missing key {key} in bank row: {bank_row!r}"

    qs_r = api.list_question_bank_questions(course_id, bank_id)
    assert qs_r.status_code == 200, qs_r.text
    qs_body = qs_r.json()
    assert isinstance(qs_body, list), qs_body
    assert len(qs_body) == 1
    q = qs_body[0]
    for key in ("questionId", "status", "promptText", "optionsJson", "correctOptionKey"):
        assert key in q, f"missing key {key} in question row: {q!r}"


def test_draft_question_banks_parity_with_modules_for_alt_teacher(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    course = course_factory(label="qb-read-parity-alt")
    course_id = course.course_id
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    lessons_r = alt_api.list_lessons(course_id)
    modules_r = alt_api.list_course_modules(course_id)
    banks_r = alt_api.list_question_banks(course_id)
    questions_r = alt_api.list_question_bank_questions(course_id, bank_id)

    assert lessons_r.status_code == modules_r.status_code == 404
    assert banks_r.status_code == modules_r.status_code
    assert questions_r.status_code == modules_r.status_code

    lb = response_json_dict(lessons_r)
    mb = response_json_dict(modules_r)
    bb = response_json_dict(banks_r)
    qb = response_json_dict(questions_r)
    assert lb.get("code") == mb.get("code"), f"lesson body {lb!r} vs modules body {mb!r}"
    assert mb.get("code") == bb.get("code"), f"modules body {mb!r} vs banks body {bb!r}"
    assert mb.get("code") == qb.get("code"), f"modules body {mb!r} vs questions body {qb!r}"


def test_draft_module_quizzes_parity_with_modules_for_alt_teacher(
    api: ApiClient, alt_api: ApiClient, course_factory
) -> None:
    """``GET .../module-quizzes`` denial matches ``GET .../modules`` on owner draft (404 + same ``code``)."""
    course = course_factory(label="qb-read-mq-parity-alt")
    course_id = course.course_id
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    lessons_r = alt_api.list_lessons(course_id)
    modules_r = alt_api.list_course_modules(course_id)
    banks_r = alt_api.list_question_banks(course_id)
    questions_r = alt_api.list_question_bank_questions(course_id, bank_id)
    mq_r = alt_api.list_module_quizzes(course_id)

    assert lessons_r.status_code == modules_r.status_code == 404
    assert mq_r.status_code == modules_r.status_code
    assert banks_r.status_code == modules_r.status_code
    assert questions_r.status_code == modules_r.status_code

    lb = response_json_dict(lessons_r)
    mb = response_json_dict(modules_r)
    mqb = response_json_dict(mq_r)
    bb = response_json_dict(banks_r)
    qb = response_json_dict(questions_r)
    assert lb.get("code") == mb.get("code"), f"lesson body {lb!r} vs modules body {mb!r}"
    assert mb.get("code") == mqb.get("code"), f"modules body {mb!r} vs module-quizzes body {mqb!r}"
    assert mb.get("code") == bb.get("code"), f"modules body {mb!r} vs banks body {bb!r}"
    assert mb.get("code") == qb.get("code"), f"modules body {mb!r} vs questions body {qb!r}"


def test_draft_question_banks_parity_with_modules_for_student(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    course = course_factory(label="qb-read-parity-student")
    course_id = course.course_id
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    lessons_r = student_api.list_lessons(course_id)
    modules_r = student_api.list_course_modules(course_id)
    banks_r = student_api.list_question_banks(course_id)
    questions_r = student_api.list_question_bank_questions(course_id, bank_id)

    assert lessons_r.status_code == modules_r.status_code == 404
    assert banks_r.status_code == modules_r.status_code
    assert questions_r.status_code == modules_r.status_code

    lb = response_json_dict(lessons_r)
    mb = response_json_dict(modules_r)
    bb = response_json_dict(banks_r)
    qb = response_json_dict(questions_r)
    assert lb.get("code") == mb.get("code"), f"lesson body {lb!r} vs modules body {mb!r}"
    assert mb.get("code") == bb.get("code"), f"modules body {mb!r} vs banks body {bb!r}"
    assert mb.get("code") == qb.get("code"), f"modules body {mb!r} vs questions body {qb!r}"


def test_draft_module_quizzes_parity_with_modules_for_student(
    api: ApiClient, student_api: ApiClient, course_factory
) -> None:
    course = course_factory(label="qb-read-mq-parity-student")
    course_id = course.course_id
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])

    lessons_r = student_api.list_lessons(course_id)
    modules_r = student_api.list_course_modules(course_id)
    banks_r = student_api.list_question_banks(course_id)
    questions_r = student_api.list_question_bank_questions(course_id, bank_id)
    mq_r = student_api.list_module_quizzes(course_id)

    assert lessons_r.status_code == modules_r.status_code == 404
    assert mq_r.status_code == modules_r.status_code
    assert banks_r.status_code == modules_r.status_code
    assert questions_r.status_code == modules_r.status_code

    lb = response_json_dict(lessons_r)
    mb = response_json_dict(modules_r)
    mqb = response_json_dict(mq_r)
    bb = response_json_dict(banks_r)
    qb = response_json_dict(questions_r)
    assert lb.get("code") == mb.get("code"), f"lesson body {lb!r} vs modules body {mb!r}"
    assert mb.get("code") == mqb.get("code"), f"modules body {mb!r} vs module-quizzes body {mqb!r}"
    assert mb.get("code") == bb.get("code"), f"modules body {mb!r} vs banks body {bb!r}"
    assert mb.get("code") == qb.get("code"), f"modules body {mb!r} vs questions body {qb!r}"


def test_owner_list_module_quizzes_after_post_quiz_with_bank(
    api: ApiClient, course_factory
) -> None:
    """Optional shape check: one module quiz row linked to a bank (RED until list + repo ship)."""
    course_id, module_id = _owner_draft_course_with_module(
        api, course_factory, label="qb-read-mq-one-row"
    )
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    qr = api.create_module_quiz(course_id, module_id, question_bank_id=bank_id)
    assert qr.status_code == 201, qr.text

    resp = api.list_module_quizzes(course_id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list), body
    assert len(body) == 1
    row = body[0]
    for key in ("quizId", "moduleId", "questionBankId", "servedCountN"):
        assert key in row, f"missing key {key} in row: {row!r}"


def test_owner_list_questions_unknown_bank_returns_404(
    api: ApiClient, course_factory
) -> None:
    course = course_factory(label="qb-read-unknown-bank")
    fake_bank_id = str(uuid.uuid4())
    resp = api.list_question_bank_questions(course.course_id, fake_bank_id)
    assert resp.status_code == 404, resp.text
    body = response_json_dict(resp)
    assert body.get("code") == "not_found"
