"""DSQL-7a S6: assignment draft, submit, grade, delete, and S3 cleanup."""

from __future__ import annotations

import os
import time

import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription
from helpers.cleanup import s3_object_exists
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.factories import make_test_title
from helpers.module_contract import require_course_modules_list

_PDF_BYTES = b"%PDF-1.4 minimal\n"
_PDF_SIZE = len(_PDF_BYTES)
_CONTENT_TYPE = "application/pdf"


def _is_dsql_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip() == "StreamMyCourse-Api-dsql"


def _wait_until_object_absent(
    bucket: str, key: str, *, region: str, timeout_s: float = 120.0, poll_s: float = 2.0
) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not s3_object_exists(bucket, key, region=region):
            return
        time.sleep(poll_s)
    assert not s3_object_exists(bucket, key, region=region)


def test_assignment_flow_draft_grade_delete(
    api: ApiClient,
    student_api: ApiClient,
    course_factory,
    lesson_factory,
    video_bucket: str,
    aws_region: str,
) -> None:
    course = course_factory(label="assign-flow")
    mods = require_course_modules_list(api.list_course_modules(course.course_id))
    module_id = mods[0]["id"]

    created = api.create_assignment(
        course.course_id,
        module_id=module_id,
        title=make_test_title("assign"),
        pass_percent=70,
        counts_toward_certificate=True,
    )
    assert created.status_code == 201, created.text
    assignment_id = created.json()["assignment"]["id"]

    crit = api.update_assignment(
        course.course_id,
        assignment_id,
        body={
            "status": "published",
            "passPercent": 70,
            "criteria": [{"label": "Work", "maxPoints": 100}],
            "instructions": {"mode": "plain", "text": "Submit a PDF"},
        },
    )
    assert crit.status_code == 200, crit.text
    criterion_id = crit.json()["assignment"]["criteria"][0]["id"]

    lesson = lesson_factory(course.course_id, label="assign-lesson")
    assert api.get_upload_url(course_id=course.course_id, lesson_id=lesson.lesson_id).status_code == 200
    assert api.mark_video_ready(course.course_id, lesson.lesson_id).status_code == 200
    assert api.publish_course(course.course_id).status_code == 200

    ensure_student_subscription(
        os.environ.get("INTEGRATION_API_BASE_URL", "").rstrip("/"),
        student_api,
        course.course_id,
        lesson.lesson_id,
    )

    open1 = student_api.open_assignment_submission(course.course_id, assignment_id)
    assert open1.status_code in (200, 201), open1.text
    submission_id = open1.json()["submission"]["id"]
    open2 = student_api.open_assignment_submission(course.course_id, assignment_id)
    assert open2.status_code in (200, 201), open2.text
    assert open2.json()["submission"]["id"] == submission_id

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            drafts = execute_scalar(
                conn,
                """
                SELECT COUNT(*) FROM app.assignment_submissions
                WHERE assignment_id = %s AND user_sub IS NOT NULL AND status = 'draft'
                """,
                (assignment_id,),
            )
        assert int(drafts or 0) == 1

    file_resp = student_api.create_submission_file(
        course.course_id,
        assignment_id,
        submission_id,
        title="paper.pdf",
        file_type="pdf",
        byte_size=_PDF_SIZE,
    )
    assert file_resp.status_code in (200, 201), file_resp.text
    body = file_resp.json()
    file_id = body["fileId"]
    upload_url = body["uploadUrl"]
    object_key = ""
    put = httpx.put(
        upload_url,
        content=_PDF_BYTES,
        headers={"Content-Type": _CONTENT_TYPE},
        timeout=30.0,
    )
    assert put.status_code == 200, put.text
    complete = student_api.complete_submission_file(
        course.course_id, assignment_id, submission_id, file_id
    )
    assert complete.status_code == 200, complete.text

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            object_key = str(
                execute_scalar(
                    conn,
                    """
                    SELECT object_key FROM app.assignment_submission_files
                    WHERE id = %s
                    """,
                    (file_id,),
                )
                or ""
            )

    submitted = student_api.submit_assignment_submission(
        course.course_id, assignment_id, submission_id
    )
    assert submitted.status_code == 200, submitted.text

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            drafts = execute_scalar(
                conn,
                """
                SELECT COUNT(*) FROM app.assignment_submissions
                WHERE assignment_id = %s AND status = 'draft'
                """,
                (assignment_id,),
            )
        assert int(drafts or 0) == 0

    graded = api.grade_assignment_submission(
        course.course_id,
        assignment_id,
        submission_id,
        scores=[{"criterionId": criterion_id, "points": 80}],
        feedback="Good",
    )
    assert graded.status_code == 200, graded.text

    deleted = api.delete_assignment(course.course_id, assignment_id)
    assert deleted.status_code == 200, deleted.text
    assert api.get_assignment(course.course_id, assignment_id).status_code == 404

    if _is_dsql_preview_stack():
        with admin_connect() as conn:
            child_n = execute_scalar(
                conn,
                """
                SELECT COUNT(*) FROM app.assignment_submissions
                WHERE assignment_id = %s
                """,
                (assignment_id,),
            )
        assert int(child_n or 0) == 0

    if object_key:
        _wait_until_object_absent(video_bucket, object_key, region=aws_region)
