"""RS-14 eligibility: required published courses + valid certificates."""

from __future__ import annotations

from services.research_team.ports import RequiredCourseRow

from tests.unit.services.research_team.helpers import (
    _COURSE_A,
    _COURSE_B,
    _STUDENT,
    make_service,
)


def test_empty_required_set_not_eligible() -> None:
    svc, *_ = make_service()
    me = svc.get_me(user_sub=_STUDENT, role="student")
    assert me["eligible"] is False
    assert me["courses"] == []
    assert me["canSubmit"] is False


def test_unpublished_flagged_course_ignored() -> None:
    """Repo only returns published required courses; draft flagged courses do not appear."""
    svc, repo, certs, *_ = make_service()
    # Simulate: only published courses are listed by the repo.
    repo.required[_COURSE_A] = RequiredCourseRow(course_id=_COURSE_A, title="Published")
    certs.statuses[(_STUDENT, _COURSE_A)] = "valid"
    me = svc.get_me(user_sub=_STUDENT, role="student")
    assert me["eligible"] is True
    assert len(me["courses"]) == 1
    assert me["courses"][0]["certified"] is True


def test_revoked_cert_not_met() -> None:
    svc, repo, certs, *_ = make_service()
    repo.required[_COURSE_A] = RequiredCourseRow(course_id=_COURSE_A, title="A")
    certs.statuses[(_STUDENT, _COURSE_A)] = "revoked"
    me = svc.get_me(user_sub=_STUDENT, role="student")
    assert me["eligible"] is False
    assert me["courses"][0]["certified"] is False
    assert me["canSubmit"] is False


def test_all_valid_certs_eligible() -> None:
    svc, repo, certs, *_ = make_service()
    repo.required[_COURSE_A] = RequiredCourseRow(course_id=_COURSE_A, title="A")
    repo.required[_COURSE_B] = RequiredCourseRow(course_id=_COURSE_B, title="B")
    certs.statuses[(_STUDENT, _COURSE_A)] = "valid"
    certs.statuses[(_STUDENT, _COURSE_B)] = "valid"
    me = svc.get_me(user_sub=_STUDENT, role="student")
    assert me["eligible"] is True
    assert me["canSubmit"] is True
    assert all(c["certified"] for c in me["courses"])
