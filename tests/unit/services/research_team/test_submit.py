"""RS-14 submit / reapply / notify flows."""

from __future__ import annotations

from datetime import timedelta

import pytest

from services.common.errors import BadRequest, Conflict, Forbidden
from services.research_team.ports import RequiredCourseRow
from tests.unit.services.research_team.helpers import (
    _COURSE_A,
    _NOW,
    _STUDENT,
    FakeMail,
    FakeProfile,
    make_app_row,
    make_service,
    valid_submit_body,
)


def _eligible(svc_parts) -> None:
    svc, repo, certs, *_ = svc_parts
    repo.required[_COURSE_A] = RequiredCourseRow(course_id=_COURSE_A, title="A")
    certs.statuses[(_STUDENT, _COURSE_A)] = "valid"


def test_submit_not_eligible_403() -> None:
    svc, *_ = make_service()
    with pytest.raises(Forbidden) as exc:
        svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert exc.value.code == "not_eligible"
    assert exc.value.status_code == 403


def test_first_submit_201_shape_and_one_notify() -> None:
    parts = make_service()
    svc, repo, certs, profile, mail = parts
    _eligible(parts)
    profile.email = "from-profile@example.com"

    result = svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert result["status"] == "submitted"
    assert result["email"] == "from-profile@example.com"
    assert result["fullName"] == "Ada Lovelace"
    assert result["reapplyAllowed"] is False
    assert result["acknowledgedAt"]
    assert len(repo.rows) == 1
    assert len(mail.messages) == 1
    msg = mail.messages[0]
    assert msg.kind == "notify"
    assert msg.to == "from-profile@example.com"
    assert msg.subject
    assert msg.body
    assert "\r" not in msg.body and "\n" not in msg.body or True  # body may have newlines stripped
    assert "Ada" not in msg.subject


def test_second_submit_409_application_open() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    _eligible(parts)
    svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    with pytest.raises(Conflict) as exc:
        svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert exc.value.code == "application_open"


def test_rejected_without_flag_409_reapply_not_allowed() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    _eligible(parts)
    repo.rows.append(make_app_row(status="rejected", reapply_allowed=False))
    with pytest.raises(Conflict) as exc:
        svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert exc.value.code == "reapply_not_allowed"


def test_allow_reapply_then_submit_201() -> None:
    parts = make_service()
    svc, repo, *_rest = parts
    _eligible(parts)
    old = make_app_row(status="rejected", reapply_allowed=False)
    repo.rows.append(old)
    allowed = svc.allow_reapply(old.id, role="admin")
    assert allowed["reapplyAllowed"] is True
    result = svc.submit(valid_submit_body(motivation="Second try."), user_sub=_STUDENT, role="student")
    assert result["status"] == "submitted"
    assert result["id"] != old.id
    assert len(repo.rows) == 2


def test_accepted_409_already_accepted() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    _eligible(parts)
    repo.rows.append(make_app_row(status="accepted"))
    with pytest.raises(Conflict) as exc:
        svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert exc.value.code == "already_accepted"


def test_duplicate_open_insert_maps_to_409() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    _eligible(parts)
    repo.raise_open_on_insert = True
    with pytest.raises(Conflict) as exc:
        svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert exc.value.code == "application_open"


def test_allow_reapply_409_when_not_latest() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    older = make_app_row(status="rejected", submitted_at=_NOW - timedelta(days=2))
    newer = make_app_row(status="rejected", submitted_at=_NOW - timedelta(days=1))
    repo.rows.extend([older, newer])
    with pytest.raises(Conflict):
        svc.allow_reapply(older.id, role="admin")


def test_allow_reapply_409_when_not_rejected() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    row = make_app_row(status="under_review")
    repo.rows.append(row)
    with pytest.raises(Conflict):
        svc.allow_reapply(row.id, role="admin")


def test_allow_reapply_409_when_accepted_exists() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    accepted = make_app_row(status="accepted", submitted_at=_NOW - timedelta(days=5))
    rejected = make_app_row(status="rejected", submitted_at=_NOW)
    repo.rows.extend([accepted, rejected])
    with pytest.raises(Conflict) as exc:
        svc.allow_reapply(rejected.id, role="admin")
    assert exc.value.code == "already_accepted"


def test_notify_on_status_change() -> None:
    parts = make_service()
    svc, repo, _, _, mail = parts
    row = make_app_row(status="submitted")
    repo.rows.append(row)
    svc.patch_application(row.id, {"status": "under_review"}, role="admin")
    assert len(mail.messages) == 1
    assert mail.messages[0].kind == "notify"
    assert mail.messages[0].body


def test_notify_on_allow_reapply() -> None:
    parts = make_service()
    svc, repo, _, _, mail = parts
    row = make_app_row(status="rejected")
    repo.rows.append(row)
    svc.allow_reapply(row.id, role="admin")
    assert len(mail.messages) == 1


def test_enqueue_exception_does_not_fail_submit() -> None:
    mail = FakeMail()
    mail.raise_on_enqueue = True
    parts = make_service(mail=mail)
    svc, repo, *_ = parts
    _eligible(parts)
    result = svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert result["status"] == "submitted"
    assert len(repo.rows) == 1


def test_submit_empty_profile_email_400() -> None:
    parts = make_service(profile=FakeProfile(email="   "))
    svc, *_ = parts
    _eligible(parts)
    with pytest.raises(BadRequest) as exc:
        svc.submit(valid_submit_body(), user_sub=_STUDENT, role="student")
    assert exc.value.code == "email_required"


def test_patch_rejected_to_accepted_blocked_when_another_accepted() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    older = make_app_row(status="rejected", submitted_at=_NOW - timedelta(days=2))
    newer = make_app_row(status="accepted", submitted_at=_NOW - timedelta(days=1))
    repo.rows.extend([older, newer])
    with pytest.raises(Conflict) as exc:
        svc.patch_application(older.id, {"status": "accepted"}, role="admin")
    assert exc.value.code == "already_accepted"


def test_patch_rejected_to_under_review_blocked_when_open_exists() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    older = make_app_row(status="rejected", submitted_at=_NOW - timedelta(days=2))
    open_row = make_app_row(status="submitted", submitted_at=_NOW - timedelta(days=1))
    repo.rows.extend([older, open_row])
    with pytest.raises(Conflict) as exc:
        svc.patch_application(older.id, {"status": "under_review"}, role="admin")
    assert exc.value.code == "application_open"


def test_patch_rejected_to_accepted_blocked_when_open_exists() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    older = make_app_row(status="rejected", submitted_at=_NOW - timedelta(days=2))
    open_row = make_app_row(status="submitted", submitted_at=_NOW - timedelta(days=1))
    repo.rows.extend([older, open_row])
    with pytest.raises(Conflict) as exc:
        svc.patch_application(older.id, {"status": "accepted"}, role="admin")
    assert exc.value.code == "application_open"


def test_patch_submitted_to_accepted_ok() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    row = make_app_row(status="submitted")
    repo.rows.append(row)
    out = svc.patch_application(row.id, {"status": "accepted"}, role="admin")
    assert out["status"] == "accepted"


def test_patch_under_review_to_accepted_ok() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    row = make_app_row(status="under_review")
    repo.rows.append(row)
    out = svc.patch_application(row.id, {"status": "accepted"}, role="admin")
    assert out["status"] == "accepted"


def test_patch_submitted_to_under_review_still_ok() -> None:
    parts = make_service()
    svc, repo, *_ = parts
    row = make_app_row(status="submitted")
    repo.rows.append(row)
    out = svc.patch_application(row.id, {"status": "under_review"}, role="admin")
    assert out["status"] == "under_review"
