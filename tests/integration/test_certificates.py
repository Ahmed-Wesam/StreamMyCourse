"""DSQL-7b S4: certificate issue, verify, revoke, and delete integration."""

from __future__ import annotations

import os
import uuid

import httpx
import pytest

from helpers.api import ApiClient
from helpers.billing_access import ensure_student_subscription
from helpers.cognito_auth import (
    admin_delete_cognito_user,
    mint_native_signup_tokens,
    resolve_student_pool_config_or_skip,
    student_client_supports_native_signup,
)
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.factories import make_test_title
from helpers.module_contract import require_course_modules_list

_PDF_BYTES = b"%PDF-1.4 minimal\n"
_PDF_SIZE = len(_PDF_BYTES)


def _is_dsql_preview_stack() -> bool:
    return os.environ.get("INTEGRATION_API_STACK", "").strip() == "StreamMyCourse-Api-dsql"


def _api_base() -> str:
    return os.environ.get("INTEGRATION_API_BASE_URL", "").rstrip("/")


def _throwaway_student_api() -> tuple[ApiClient, object, str]:
    pool = resolve_student_pool_config_or_skip()
    student_client_supports_native_signup(pool)
    email = f"cert-{uuid.uuid4().hex[:12]}@noreply.local"
    password = f"Cert-Test-{uuid.uuid4().hex[:8]}!aA1"
    tokens = mint_native_signup_tokens(cfg=pool, email=email, password=password)
    client = httpx.Client(
        base_url=_api_base(),
        headers={"Authorization": f"Bearer {tokens.id_token}"},
        timeout=60.0,
    )
    return ApiClient(client), pool, email


def _grade_passing_assignment(
    teacher: ApiClient,
    student: ApiClient,
    course_id: str,
    *,
    counts_toward_certificate: bool = True,
) -> None:
    mods = require_course_modules_list(teacher.list_course_modules(course_id))
    module_id = mods[0]["id"]
    created = teacher.create_assignment(
        course_id,
        module_id=module_id,
        title=make_test_title("cert-assign"),
        pass_percent=70,
        counts_toward_certificate=counts_toward_certificate,
    )
    assert created.status_code == 201, created.text
    assignment_id = created.json()["assignment"]["id"]
    crit = teacher.update_assignment(
        course_id,
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
    lesson_list = teacher.list_lessons(course_id)
    if lesson_list.status_code != 200 or not lesson_list.json():
        from helpers.factories import build_lesson_factory

        lf = build_lesson_factory(teacher)
        lesson = lf(course_id, label="cert-lesson")
        assert teacher.get_upload_url(course_id=course_id, lesson_id=lesson.lesson_id).status_code == 200
        assert teacher.mark_video_ready(course_id, lesson.lesson_id).status_code == 200
        lesson_id = lesson.lesson_id
    else:
        lesson_id = lesson_list.json()[0]["id"]
    course_meta = teacher.get_course(course_id)
    if course_meta.status_code == 200 and course_meta.json().get("status") != "PUBLISHED":
        assert teacher.mark_video_ready(course_id, lesson_id).status_code == 200
        assert teacher.publish_course(course_id).status_code == 200
    ensure_student_subscription(_api_base(), student, course_id, lesson_id)
    open_sub = student.open_assignment_submission(course_id, assignment_id)
    assert open_sub.status_code in (200, 201), open_sub.text
    submission_id = open_sub.json()["submission"]["id"]
    file_resp = student.create_submission_file(
        course_id,
        assignment_id,
        submission_id,
        title="paper.pdf",
        file_type="pdf",
        byte_size=_PDF_SIZE,
    )
    assert file_resp.status_code in (200, 201), file_resp.text
    file_id = file_resp.json()["fileId"]
    put = httpx.put(
        file_resp.json()["uploadUrl"],
        content=_PDF_BYTES,
        headers={"Content-Type": "application/pdf"},
        timeout=30.0,
    )
    assert put.status_code == 200, put.text
    assert (
        student.complete_submission_file(course_id, assignment_id, submission_id, file_id).status_code
        == 200
    )
    assert (
        student.submit_assignment_submission(course_id, assignment_id, submission_id).status_code
        == 200
    )
    graded = teacher.grade_assignment_submission(
        course_id,
        assignment_id,
        submission_id,
        scores=[{"criterionId": criterion_id, "points": 90}],
    )
    assert graded.status_code == 200, graded.text


def test_certificate_issue_verify_and_revoke(
    api: ApiClient,
    course_factory,
) -> None:
    throwaway, pool, email = _throwaway_student_api()
    try:
        throwaway.patch_users_me(
            body={"givenName": "Cert", "familyName": "Student", "country": "Jordan"}
        )
        course = course_factory(label="cert-issue")
        _grade_passing_assignment(api, throwaway, course.course_id)
        first = throwaway.get_my_certificates()
        assert first.status_code == 200, first.text
        certs = [c for c in first.json().get("certificates", []) if c.get("kind") != "bundle"]
        assert len(certs) == 1
        credential_id = certs[0]["credentialId"]
        certificate_id = certs[0]["id"]
        second = throwaway.get_my_certificates()
        assert second.json()["certificates"][0]["credentialId"] == credential_id
        assert throwaway.get_certificate_public(credential_id).status_code == 200
        flipped = credential_id.swapcase()
        if flipped != credential_id:
            assert throwaway.get_certificate_public(flipped).status_code == 200
        revoked = api.revoke_course_certificate(course.course_id, certificate_id)
        assert revoked.status_code == 200, revoked.text
        assert revoked.json().get("status") == "revoked"
        after = throwaway.get_my_certificates()
        rows = [c for c in after.json().get("certificates", []) if c.get("id") == certificate_id]
        assert len(rows) == 1
        assert rows[0]["status"] == "revoked"
        public = throwaway.get_certificate_public(credential_id)
        assert public.status_code == 200
        assert public.json().get("status") == "revoked"
        if _is_dsql_preview_stack():
            with admin_connect() as conn:
                count = execute_scalar(
                    conn,
                    "SELECT COUNT(*) FROM app.certificates WHERE course_id = %s",
                    (course.course_id,),
                )
            assert int(count or 0) == 1
    finally:
        throwaway.raw.close()
        admin_delete_cognito_user(cfg=pool, username=email)


def test_course_delete_removes_certificates_preview_only(
    api: ApiClient,
    course_factory,
) -> None:
    if not _is_dsql_preview_stack():
        pytest.skip("preview SQL assert only on StreamMyCourse-Api-dsql")
    throwaway, pool, email = _throwaway_student_api()
    course = None
    try:
        throwaway.patch_users_me(body={"givenName": "Cert", "familyName": "Del"})
        course = course_factory(label="cert-course-del")
        _grade_passing_assignment(api, throwaway, course.course_id)
        assert throwaway.get_my_certificates().status_code == 200
        course_id = course.course_id
        deleted = api.delete_course(course_id)
        assert deleted.status_code in (200, 202, 204), deleted.text
        assert api.get_course(course_id).status_code == 404
        with admin_connect() as conn:
            count = execute_scalar(
                conn,
                "SELECT COUNT(*) FROM app.certificates WHERE course_id = %s",
                (course_id,),
            )
        assert int(count or 0) == 0
        course = None
    finally:
        throwaway.raw.close()
        admin_delete_cognito_user(cfg=pool, username=email)
        if course is not None:
            api.delete_course(course.course_id)
