"""HTTPS integration tests for ``POST .../modules/{moduleId}/quiz/submit`` (QB-H).

Happy-path grading, validation (partial answers → 400), double submit → 409,
IDOR on path ``courseId``, post-submit ``start`` summaries vs ``retake``, and
response leak scans for ``correctOptionKey``.

See ``tests/integration/test_question_bank_start.py`` (shared setup helpers) and
``tests/integration/README.md``.
"""

from __future__ import annotations

from typing import Any

import pytest

from helpers.api import ApiClient
from helpers.module_contract import response_json_dict

from test_question_bank_start import (
    _assert_no_start_response_leaks,
    _publish_bank_and_course,
    _question_ids_from_start,
)


def _answers_all_first_choice(body: dict[str, Any]) -> dict[str, str]:
    """Map each served question id → first MCQ option key from ``optionsJson``."""
    out: dict[str, str] = {}
    for question in body.get("questions") or []:
        assert isinstance(question, dict), f"expected question object, got {question!r}"
        qid = str(question["id"])
        options = question.get("optionsJson")
        assert isinstance(options, list) and options, f"expected optionsJson for {qid!r}"
        first = options[0]
        assert isinstance(first, dict) and first.get("key"), f"bad option row {first!r}"
        out[qid] = str(first["key"])
    return out


def _paths_for_json_key(obj: Any, target_key: str, path: tuple[str, ...] = ()) -> list[tuple[str, ...]]:
    found: list[tuple[str, ...]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            seg = path + (k,)
            if k == target_key:
                found.append(seg)
            found.extend(_paths_for_json_key(v, target_key, seg))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            found.extend(_paths_for_json_key(item, target_key, path + (str(i),)))
    return found


def _assert_correct_option_key_only_under_latest_submission_questions(body: dict[str, Any]) -> None:
    """``correctOptionKey`` may appear only under ``latestSubmission.questions[*]``.

    Paths look like ``("latestSubmission", "questions", "0", "correctOptionKey")`` —
    length **4**, not 5 (_paths_for_json_key uses string indices only).
    """
    for p in _paths_for_json_key(body, "correctOptionKey"):
        if (
            len(p) >= 4
            and p[-1] == "correctOptionKey"
            and p[-4] == "latestSubmission"
            and p[-3] == "questions"
        ):
            continue
        pytest.fail(f"leak scan: correctOptionKey at forbidden path {p!r}")


def test_submit_happy_path_returns_scored_breakdown(
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
        label="qb-submit-happy",
        served_n=served_n,
    )

    start = student_api.start_module_quiz(course_id, module_id)
    assert start.status_code == 200, start.text
    start_body = response_json_dict(start)
    _assert_no_start_response_leaks(start_body)
    attempt_id = str(start_body["attemptId"])
    answers = _answers_all_first_choice(start_body)

    sub = student_api.submit_module_quiz(
        course_id,
        module_id,
        {"attemptId": attempt_id, "answers": answers},
    )
    assert sub.status_code == 200, sub.text
    body = response_json_dict(sub)
    assert body.get("attemptId") == attempt_id
    assert body.get("attemptNumber") == 1
    assert body.get("totalCount") == served_n
    assert isinstance(body.get("correctCount"), int)
    qs = body.get("questions")
    assert isinstance(qs, list) and len(qs) == served_n
    for row in qs:
        assert isinstance(row, dict)
        for key in ("id", "promptText", "selectedOptionKey", "correctOptionKey", "isCorrect"):
            assert key in row


def test_submit_partial_answers_returns_400(
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
        label="qb-submit-partial",
        served_n=served_n,
    )

    start = student_api.start_module_quiz(course_id, module_id)
    assert start.status_code == 200, start.text
    start_body = response_json_dict(start)
    attempt_id = str(start_body["attemptId"])
    answers = _answers_all_first_choice(start_body)
    ids = _question_ids_from_start(start_body)
    assert len(ids) == served_n
    partial = {ids[0]: answers[ids[0]]}

    sub = student_api.submit_module_quiz(
        course_id,
        module_id,
        {"attemptId": attempt_id, "answers": partial},
    )
    assert sub.status_code == 400, sub.text
    err = response_json_dict(sub)
    assert err.get("code") == "bad_request"


def test_double_submit_returns_409(
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
        label="qb-submit-double",
        served_n=served_n,
    )

    start = student_api.start_module_quiz(course_id, module_id)
    assert start.status_code == 200, start.text
    start_body = response_json_dict(start)
    attempt_id = str(start_body["attemptId"])
    payload = {"attemptId": attempt_id, "answers": _answers_all_first_choice(start_body)}

    first = student_api.submit_module_quiz(course_id, module_id, payload)
    assert first.status_code == 200, first.text

    second = student_api.submit_module_quiz(course_id, module_id, payload)
    assert second.status_code == 409, second.text
    err = response_json_dict(second)
    assert err.get("code") == "conflict"


def test_submit_wrong_course_id_returns_404(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """IDOR: attempt started under course A must not submit under course B path."""
    served_n = 2
    course_a_id, module_a_id = _publish_bank_and_course(
        api,
        student_api,
        course_factory,
        lesson_factory,
        label="qb-submit-idor-a",
        served_n=served_n,
    )
    course_b = course_factory(label="qb-submit-idor-b")
    course_b_id = course_b.course_id

    start = student_api.start_module_quiz(course_a_id, module_a_id)
    assert start.status_code == 200, start.text
    start_body = response_json_dict(start)
    attempt_id = str(start_body["attemptId"])
    payload = {"attemptId": attempt_id, "answers": _answers_all_first_choice(start_body)}

    sub = student_api.submit_module_quiz(course_b_id, module_a_id, payload)
    assert sub.status_code == 404, (
        f"wrong courseId in path must not submit attempt from {course_a_id!r}; "
        f"got {sub.status_code}: {sub.text}"
    )
    err = response_json_dict(sub)
    assert err.get("code") == "not_found"


def test_after_submit_start_default_shows_latest_results_retake_starts_new_attempt(
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
        label="qb-submit-start-phases",
        served_n=served_n,
    )

    start1 = student_api.start_module_quiz(course_id, module_id)
    assert start1.status_code == 200, start1.text
    body1 = response_json_dict(start1)
    _assert_no_start_response_leaks(body1)
    attempt_id = str(body1["attemptId"])

    sub = student_api.submit_module_quiz(
        course_id,
        module_id,
        {"attemptId": attempt_id, "answers": _answers_all_first_choice(body1)},
    )
    assert sub.status_code == 200, sub.text

    latest = student_api.start_module_quiz(course_id, module_id)
    assert latest.status_code == 200, latest.text
    latest_body = response_json_dict(latest)
    assert latest_body.get("phase") == "latest_results"
    assert latest_body.get("moduleId") == module_id
    ls = latest_body.get("latestSubmission")
    assert isinstance(ls, dict), f"expected latestSubmission object, got {ls!r}"
    assert ls.get("attemptNumber") == 1
    assert ls.get("totalCount") == served_n
    qs = ls.get("questions")
    assert isinstance(qs, list) and len(qs) == served_n
    for row in qs:
        assert isinstance(row, dict)
        assert "correctOptionKey" in row
    _assert_correct_option_key_only_under_latest_submission_questions(latest_body)

    retake = student_api.start_module_quiz(course_id, module_id, body={"retake": True})
    assert retake.status_code == 200, retake.text
    retake_body = response_json_dict(retake)
    assert retake_body.get("phase") == "in_progress"
    assert retake_body.get("attemptNumber") == 2
    assert retake_body.get("attemptId") != attempt_id
    _assert_no_start_response_leaks(retake_body)


def test_in_progress_start_never_exposes_correct_option_key_latest_results_allows_it(
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
        label="qb-submit-leak-scan",
        served_n=served_n,
    )

    start_ip = student_api.start_module_quiz(course_id, module_id)
    assert start_ip.status_code == 200, start_ip.text
    ip_body = response_json_dict(start_ip)
    assert ip_body.get("phase") == "in_progress"
    assert not _paths_for_json_key(ip_body, "correctOptionKey")
    _assert_no_start_response_leaks(ip_body)

    attempt_id = str(ip_body["attemptId"])
    assert (
        student_api.submit_module_quiz(
            course_id,
            module_id,
            {"attemptId": attempt_id, "answers": _answers_all_first_choice(ip_body)},
        ).status_code
        == 200
    )

    results = student_api.start_module_quiz(course_id, module_id)
    assert results.status_code == 200, results.text
    lr_body = response_json_dict(results)
    assert lr_body.get("phase") == "latest_results"
    paths = _paths_for_json_key(lr_body, "correctOptionKey")
    assert paths, "latest_results should expose correctOptionKey under latestSubmission.questions"
    _assert_correct_option_key_only_under_latest_submission_questions(lr_body)
