"""HTTPS coverage for lesson file create / complete / list / delete (DSQL-3 S5)."""

from __future__ import annotations

import httpx

from helpers.api import ApiClient
from helpers.factories import make_test_title

_PDF_BYTES = b"%PDF-1.4 minimal\n"
_PDF_SIZE = len(_PDF_BYTES)
_CONTENT_TYPE = "application/pdf"


def _create_ready_lesson_file(
    api: ApiClient, course_id: str, lesson_id: str, *, title: str | None = None
) -> str:
    title = title or make_test_title("lesson-file")
    created = api.create_lesson_file(
        course_id,
        lesson_id,
        title=title,
        kind="resource",
        file_type="pdf",
        byte_size=_PDF_SIZE,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    file_id = str(body["fileId"])
    upload_url = str(body["uploadUrl"])
    put = httpx.put(
        upload_url,
        content=_PDF_BYTES,
        headers={"Content-Type": _CONTENT_TYPE},
        timeout=30.0,
    )
    assert put.status_code == 200, put.text
    completed = api.complete_lesson_file(course_id, lesson_id, file_id)
    assert completed.status_code == 200, completed.text
    assert completed.json().get("status") == "ready"
    return file_id


def test_lesson_file_create_complete_list_delete(api: ApiClient, course_factory, lesson_factory) -> None:
    course = course_factory(label="lesson-files-crud")
    lesson = lesson_factory(course.course_id, label="with-file")
    file_id = _create_ready_lesson_file(api, course.course_id, lesson.lesson_id)

    listed = api.list_lesson_files(course.course_id, lesson.lesson_id)
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["fileId"] == file_id
    assert rows[0]["status"] == "ready"

    deleted = api.delete_lesson_file(course.course_id, lesson.lesson_id, file_id)
    assert deleted.status_code == 200, deleted.text

    after = api.list_lesson_files(course.course_id, lesson.lesson_id)
    assert after.status_code == 200, after.text
    assert after.json() == []

    assert api.delete_course(course.course_id).status_code == 200
    gone = api.get_course(course.course_id)
    assert gone.status_code == 404, gone.text
    assert gone.json().get("code") == "not_found"