"""RS-14 authz, PATCH semantics, profile email snapshot."""

from __future__ import annotations

import pytest

from services.common.errors import Conflict, Forbidden
from services.research_team.ports import RequiredCourseRow
from tests.unit.services.research_team.helpers import (
    _COURSE_A,
    _STUDENT,
    make_app_row,
    make_service,
    valid_submit_body,
)


@pytest.mark.parametrize(
    "role",
    ["student", "teacher"],
)
def test_non_admin_forbidden_on_admin_routes(role: str) -> None:
    svc, repo, *_ = make_service()
    row = make_app_row()
    repo.rows.append(row)
    repo.courses_exist.add(_COURSE_A)

    with pytest.raises(Forbidden):
        svc.list_applications(role=role)
    with pytest.raises(Forbidden):
        svc.get_application(row.id, role=role)
    with pytest.raises(Forbidden):
        svc.patch_application(row.id, {"status": "under_review"}, role=role)
    with pytest.raises(Forbidden):
        svc.allow_reapply(row.id, role=role)
    with pytest.raises(Forbidden):
        svc.set_requirement(_COURSE_A, {"required": True}, role=role)
    with pytest.raises(Forbidden):
        svc.get_requirement(_COURSE_A, role=role)


def test_admin_get_requirement_includes_unpublished() -> None:
    svc, repo, *_ = make_service()
    repo.courses_exist.add(_COURSE_A)
    repo.set_requirement(_COURSE_A, required=True)
    out = svc.get_requirement(_COURSE_A, role="admin")
    assert out == {"courseId": _COURSE_A, "required": True}
    assert repo.is_required(_COURSE_A) is True


def test_non_admin_forbidden_get_requirement() -> None:
    svc, repo, *_ = make_service()
    repo.courses_exist.add(_COURSE_A)
    with pytest.raises(Forbidden):
        svc.get_requirement(_COURSE_A, role="teacher")


def test_admin_put_requirement_without_course_ownership() -> None:
    svc, repo, *_ = make_service()
    repo.courses_exist.add(_COURSE_A)
    result = svc.set_requirement(_COURSE_A, {"required": True}, role="admin")
    assert result == {"courseId": _COURSE_A, "required": True}
    assert _COURSE_A in repo.required


def test_patch_ignores_reapply_allowed_in_body() -> None:
    svc, repo, *_ = make_service()
    row = make_app_row(status="submitted", reapply_allowed=False)
    repo.rows.append(row)
    result = svc.patch_application(
        row.id,
        {"status": "under_review", "reapplyAllowed": True},
        role="admin",
    )
    assert result["status"] == "under_review"
    assert result["reapplyAllowed"] is False


def test_same_status_patch_sends_no_mail() -> None:
    svc, repo, _, _, mail = make_service()
    row = make_app_row(status="submitted")
    repo.rows.append(row)
    result = svc.patch_application(row.id, {"status": "submitted"}, role="admin")
    assert result["status"] == "submitted"
    assert mail.messages == []


def test_post_email_field_ignored_uses_profile() -> None:
    parts = make_service()
    svc, repo, certs, profile, _ = parts
    repo.required[_COURSE_A] = RequiredCourseRow(course_id=_COURSE_A, title="A")
    certs.statuses[(_STUDENT, _COURSE_A)] = "valid"
    profile.email = "canonical@example.com"
    result = svc.submit(
        valid_submit_body(email="spoofed@evil.com"),
        user_sub=_STUDENT,
        role="student",
    )
    assert result["email"] == "canonical@example.com"
    assert repo.rows[0].email == "canonical@example.com"


def test_teacher_cannot_get_me() -> None:
    svc, *_ = make_service()
    with pytest.raises(Forbidden):
        svc.get_me(user_sub=_STUDENT, role="teacher")


def test_admin_cannot_change_accepted_row() -> None:
    svc, repo, *_ = make_service()
    row = make_app_row(status="accepted")
    repo.rows.append(row)
    with pytest.raises(Conflict) as exc:
        svc.patch_application(row.id, {"status": "rejected"}, role="admin")
    assert exc.value.code == "already_accepted"


def test_admin_may_patch_rejected_to_accepted() -> None:
    svc, repo, _, _, mail = make_service()
    row = make_app_row(status="rejected")
    repo.rows.append(row)
    result = svc.patch_application(row.id, {"status": "accepted"}, role="admin")
    assert result["status"] == "accepted"
    assert len(mail.messages) == 1
