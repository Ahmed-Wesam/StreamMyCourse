"""Catalog delete regression: modules, lessons, courses (DSQL-3 S5)."""

from __future__ import annotations

import httpx

from helpers.api import ApiClient
from helpers.factories import make_test_title
from helpers.module_contract import require_course_modules_list, require_lessons_include_module_fields

_PDF_BYTES = b"%PDF-1.4 minimal\n"
_PDF_SIZE = len(_PDF_BYTES)
_CONTENT_TYPE = "application/pdf"


def _create_ready_lesson_file(api: ApiClient, course_id: str, lesson_id: str) -> str:
    created = api.create_lesson_file(
        course_id,
        lesson_id,
        title=make_test_title("attach-file"),
        kind="resource",
        file_type="pdf",
        byte_size=_PDF_SIZE,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    file_id = str(body["fileId"])
    put = httpx.put(
        str(body["uploadUrl"]),
        content=_PDF_BYTES,
        headers={"Content-Type": _CONTENT_TYPE},
        timeout=30.0,
    )
    assert put.status_code == 200, put.text
    assert api.complete_lesson_file(course_id, lesson_id, file_id).status_code == 200
    return file_id


def test_delete_module_removes_lesson_and_file(api: ApiClient, course_factory) -> None:
    course = course_factory(label="cat-del-mod")
    mods = require_course_modules_list(api.list_course_modules(course.course_id))
    default_id = min(mods, key=lambda m: int(m["order"]))["id"]

    extra = api.create_course_module(
        course.course_id, title=make_test_title("victim-mod"), description=""
    )
    assert extra.status_code == 201, extra.text
    victim_id = extra.json()["moduleId"]

    lr = api.create_lesson(
        course.course_id, title=make_test_title("mod-lesson"), module_id=victim_id
    )
    assert lr.status_code == 201, lr.text
    lesson_id = lr.json()["lessonId"]
    _create_ready_lesson_file(api, course.course_id, lesson_id)

    assert api.delete_course_module(course.course_id, victim_id).status_code == 200

    lessons = require_lessons_include_module_fields(api.list_lessons(course.course_id))
    assert lesson_id not in {x["id"] for x in lessons}

    remaining = require_course_modules_list(api.list_course_modules(course.course_id))
    assert len(remaining) == 1
    assert remaining[0]["id"] == default_id

    assert api.delete_course(course.course_id).status_code == 200


def test_delete_lesson_removes_file_and_compacts_sibling(
    api: ApiClient, course_factory, lesson_factory
) -> None:
    course = course_factory(label="cat-del-lesson")
    a = lesson_factory(course.course_id, label="keep")
    b = lesson_factory(course.course_id, label="drop")
    assert (a.order, b.order) == (1, 2)
    _create_ready_lesson_file(api, course.course_id, b.lesson_id)

    assert api.delete_lesson(course.course_id, b.lesson_id).status_code == 200

    listed = require_lessons_include_module_fields(api.list_lessons(course.course_id))
    assert len(listed) == 1
    assert listed[0]["id"] == a.lesson_id
    assert listed[0]["order"] == 1

    assert api.delete_course(course.course_id).status_code == 200


def test_delete_course_removes_catalog_rows(api: ApiClient, course_factory, lesson_factory) -> None:
    course = course_factory(label="cat-del-course")
    lesson = lesson_factory(course.course_id, label="course-file")
    _create_ready_lesson_file(api, course.course_id, lesson.lesson_id)

    assert api.delete_course(course.course_id).status_code == 200
    assert api.get_course(course.course_id).status_code == 404


def test_delete_last_module_still_bad_request(api: ApiClient, course_factory) -> None:
    course = course_factory(label="cat-del-last-mod")
    mods = require_course_modules_list(api.list_course_modules(course.course_id))
    assert len(mods) == 1
    only_id = mods[0]["id"]

    resp = api.delete_course_module(course.course_id, only_id)
    assert resp.status_code == 400, resp.text
    assert resp.json().get("code") == "bad_request"

    assert api.delete_course(course.course_id).status_code == 200


def _mcq_options() -> list[dict[str, str]]:
    return [{"key": "A", "text": "First"}, {"key": "B", "text": "Second"}]


def _setup_published_quiz_on_module(
    api: ApiClient,
    course_id: str,
    module_id: str,
    *,
    served_n: int = 2,
) -> str:
    br = api.create_question_bank(course_id)
    assert br.status_code == 201, br.text
    bank_id = str(br.json()["questionBankId"])
    assert (
        api.create_module_quiz(course_id, module_id, question_bank_id=bank_id).status_code == 201
    )
    for i in range(served_n):
        dr = api.create_draft_question(
            course_id,
            bank_id,
            prompt_text=f"Del quiz Q{i + 1}?",
            options_json=_mcq_options(),
            correct_option_key="A",
        )
        assert dr.status_code == 201, dr.text
    pub = api.publish_question_bank(course_id, bank_id, n=served_n, module_id=module_id)
    assert pub.status_code == 200, pub.text
    return bank_id


def test_delete_module_removes_quiz_rows_leaves_question_bank(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
) -> None:
    """DSQL-6 S6: module delete clears quiz + student rows; bank and questions stay."""
    from helpers.billing_access import ensure_student_subscription

    served_n = 2
    course = course_factory(label="cat-del-qb-mod")
    course_id = course.course_id

    extra = api.create_course_module(
        course_id, title=make_test_title("quiz-victim-mod"), description=""
    )
    assert extra.status_code == 201, extra.text
    victim_id = str(extra.json()["moduleId"])

    _setup_published_quiz_on_module(api, course_id, victim_id, served_n=served_n)
    lesson = lesson_factory(course_id, label="cat-del-qb-lesson")
    upload_resp = api.get_upload_url(course_id=course_id, lesson_id=lesson.lesson_id)
    assert upload_resp.status_code == 200, upload_resp.text
    assert api.mark_video_ready(course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course_id).status_code == 200
    ensure_student_subscription(api_base_url, student_api, course_id, lesson.lesson_id)

    start = student_api.start_module_quiz(course_id, victim_id)
    assert start.status_code == 200, start.text

    assert api.delete_course_module(course_id, victim_id).status_code == 200

    quiz_rows = [
        row
        for row in api.list_module_quizzes(course_id).json()
        if str(row.get("moduleId")) == victim_id
    ]
    assert quiz_rows == []
    assert student_api.start_module_quiz(course_id, victim_id).status_code == 404

    assert api.delete_course(course_id).status_code == 200


def test_delete_module_removes_assignment_submission_and_s3(
    api_base_url: str,
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
) -> None:
    """DSQL-7a: module delete clears assignment submission rows over HTTPS."""
    from helpers.billing_access import ensure_student_subscription

    course = course_factory(label="cat-del-assign-mod")
    course_id = course.course_id
    extra = api.create_course_module(
        course_id, title=make_test_title("assign-victim-mod"), description=""
    )
    assert extra.status_code == 201, extra.text
    victim_id = str(extra.json()["moduleId"])
    created = api.create_assignment(
        course_id,
        module_id=victim_id,
        title=make_test_title("mod-assign"),
        pass_percent=70,
    )
    assert created.status_code == 201, created.text
    assignment_id = created.json()["assignment"]["id"]
    pub = api.update_assignment(
        course_id,
        assignment_id,
        body={
            "status": "published",
            "criteria": [{"label": "R", "maxPoints": 10}],
            "instructions": {"mode": "plain", "text": "x"},
        },
    )
    assert pub.status_code == 200, pub.text
    lr = api.create_lesson(
        course_id, title=make_test_title("assign-mod-lesson"), module_id=victim_id
    )
    assert lr.status_code == 201, lr.text
    lesson_id = lr.json()["lessonId"]
    assert api.get_upload_url(course_id=course_id, lesson_id=lesson_id).status_code == 200
    assert api.mark_video_ready(course_id, lesson_id).status_code == 200
    assert api.publish_course(course_id).status_code == 200
    ensure_student_subscription(api_base_url, student_api, course_id, lesson_id)
    open_sub = student_api.open_assignment_submission(course_id, assignment_id)
    assert open_sub.status_code in (200, 201), open_sub.text
    sid = open_sub.json()["submission"]["id"]
    fr = student_api.create_submission_file(
        course_id, assignment_id, sid, title="f.pdf", file_type="pdf", byte_size=_PDF_SIZE
    )
    assert fr.status_code in (200, 201), fr.text
    fid = fr.json()["fileId"]
    put = httpx.put(
        fr.json()["uploadUrl"],
        content=_PDF_BYTES,
        headers={"Content-Type": _CONTENT_TYPE},
        timeout=30.0,
    )
    assert put.status_code == 200
    assert (
        student_api.complete_submission_file(course_id, assignment_id, sid, fid).status_code
        == 200
    )
    assert api.delete_course_module(course_id, victim_id).status_code == 200
    assert api.delete_course(course_id).status_code == 200