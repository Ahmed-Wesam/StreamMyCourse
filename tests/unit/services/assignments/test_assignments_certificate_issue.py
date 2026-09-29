"""RS-12: assignment pass hooks CertificatesService.try_issue (fakes only)."""

from __future__ import annotations

from typing import Any

from services.assignments.ports import ObjectHead
from services.assignments.service import AssignmentsService

from tests.unit.services.assignments.test_assignments_service import (
    _COURSE,
    _MOD1,
    _STUDENT,
    _TEACHER,
    FakeCleanup,
    FakeCourseAccess,
    FakeCourseLookup,
    FakeMail,
    FakeQuizLock,
    FakeStorage,
    FakeUserEmail,
    InMemoryAssignmentsRepo,
    _create_publishable,
)


class _FakeIssuer:
    def __init__(self, *, raise_on_issue: bool = False) -> None:
        self.calls: list[dict[str, str]] = []
        self.raise_on_issue = raise_on_issue

    def try_issue(self, *, user_sub: str, course_id: str, role: str) -> Any:
        self.calls.append(
            {"user_sub": user_sub, "course_id": course_id, "role": role}
        )
        if self.raise_on_issue:
            raise RuntimeError("issuer exploded")
        return None


def _harness(*, issuer: _FakeIssuer | None = None) -> dict:
    repo = InMemoryAssignmentsRepo()
    storage = FakeStorage()
    cleanup = FakeCleanup()
    mail = FakeMail()
    user_email = FakeUserEmail()
    access = FakeCourseAccess()
    lock = FakeQuizLock()
    courses = FakeCourseLookup()
    svc = AssignmentsService(
        repo=repo,
        storage=storage,
        course_access=access,
        quiz_lock=lock,
        course_lookup=courses,
        cleanup=cleanup,
        mail=mail,
        user_email=user_email,
        certificate_issuer=issuer,
    )
    return {
        "svc": svc,
        "repo": repo,
        "storage": storage,
        "issuer": issuer,
    }


def _submit_ready(h: dict) -> tuple[str, str, str]:
    """Publish assignment, student submits; return (aid, sid, criterion_id)."""
    svc: AssignmentsService = h["svc"]
    aid = _create_publishable(h)
    svc.update_assignment(
        _COURSE,
        aid,
        cognito_sub=_TEACHER,
        role="teacher",
        body={
            "passPercent": 70,
            "criteria": [{"label": "All", "maxPoints": 100}],
            "instructions": {"mode": "plain", "text": "Score me"},
            "status": "published",
        },
    )
    opened = svc.open_draft_submission(
        _COURSE, aid, cognito_sub=_STUDENT, role="student"
    )
    sid = opened["submission"]["id"]
    created_f = svc.create_submission_file(
        _COURSE,
        aid,
        sid,
        title="f",
        file_type="pdf",
        byte_size=10,
        cognito_sub=_STUDENT,
        role="student",
    )
    frow = h["repo"].files[created_f["fileId"]]
    h["storage"].objects[frow.object_key] = ObjectHead(
        content_type=frow.content_type, content_length=10
    )
    svc.complete_submission_file(
        _COURSE,
        aid,
        sid,
        created_f["fileId"],
        cognito_sub=_STUDENT,
        role="student",
    )
    svc.submit_submission(
        _COURSE, aid, sid, cognito_sub=_STUDENT, role="student", body={}
    )
    cid = h["repo"].assignments[aid].criteria[0].id
    return aid, sid, cid


def test_passing_grade_calls_try_issue_with_student_sub() -> None:
    issuer = _FakeIssuer()
    h = _harness(issuer=issuer)
    svc: AssignmentsService = h["svc"]
    aid, sid, cid = _submit_ready(h)

    result = svc.grade_submission(
        _COURSE,
        aid,
        sid,
        scores=[{"criterionId": cid, "points": 80}],
        feedback="Nice work on this assignment.",
        cognito_sub=_TEACHER,
        role="teacher",
        body={
            "scores": [{"criterionId": cid, "points": 80}],
            "feedback": "Nice work on this assignment.",
        },
    )

    assert result["passed"] is True
    assert issuer.calls == [
        {"user_sub": _STUDENT, "course_id": _COURSE, "role": "student"}
    ]
    assert issuer.calls[0]["user_sub"] != _TEACHER


def test_failing_grade_does_not_call_try_issue() -> None:
    issuer = _FakeIssuer()
    h = _harness(issuer=issuer)
    svc: AssignmentsService = h["svc"]
    aid, sid, cid = _submit_ready(h)

    result = svc.grade_submission(
        _COURSE,
        aid,
        sid,
        scores=[{"criterionId": cid, "points": 50}],
        feedback="Needs more work to pass.",
        cognito_sub=_TEACHER,
        role="teacher",
        body={
            "scores": [{"criterionId": cid, "points": 50}],
            "feedback": "Needs more work to pass.",
        },
    )

    assert result["passed"] is False
    assert issuer.calls == []


def test_raising_issuer_does_not_fail_passing_grade() -> None:
    issuer = _FakeIssuer(raise_on_issue=True)
    h = _harness(issuer=issuer)
    svc: AssignmentsService = h["svc"]
    aid, sid, cid = _submit_ready(h)

    result = svc.grade_submission(
        _COURSE,
        aid,
        sid,
        scores=[{"criterionId": cid, "points": 90}],
        feedback="Excellent submission overall.",
        cognito_sub=_TEACHER,
        role="teacher",
        body={
            "scores": [{"criterionId": cid, "points": 90}],
            "feedback": "Excellent submission overall.",
        },
    )

    assert result["passed"] is True
    assert result["scorePercent"] == 90
    assert len(issuer.calls) == 1
