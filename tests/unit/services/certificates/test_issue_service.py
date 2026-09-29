"""RS-12 certificates issue/lookup/revoke service tests (fakes only; no AWS/Postgres)."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence

import pytest

from services.certificates.eligibility import AssignmentRequirement, QuizRequirement
from services.certificates.ports import CertificateRow, CourseInfo
from services.common.errors import BadRequest, Forbidden, NotFound

_COURSE = "11111111-1111-1111-1111-111111111111"
_COURSE_B = "22222222-2222-2222-2222-222222222222"
_TEACHER = "teacher-owner"
_OTHER_TEACHER = "teacher-other"
_STUDENT = "student-1"
_CODE = "A1B7F3"
_CREDENTIAL_RE = re.compile(r"^RS-[0-9A-F]{6}-[0-9]{4}-[0-9A-F]{10}$")
_FIXED_NOW = datetime(2026, 9, 15, 12, 0, 0, tzinfo=timezone.utc)


class FakeRepo:
    def __init__(self) -> None:
        self.rows: Dict[str, CertificateRow] = {}
        self.by_user_course: Dict[tuple[str, str], str] = {}
        self.insert_calls = 0
        self.lookup_calls = 0

    def insert_certificate(self, row: CertificateRow) -> CertificateRow:
        self.insert_calls += 1
        key = (row.user_sub, row.course_id)
        if key in self.by_user_course:
            existing = self.rows[self.by_user_course[key]]
            return existing
        self.rows[row.id] = row
        self.by_user_course[key] = row.id
        return row

    def get_by_credential_id(self, credential_id: str) -> Optional[CertificateRow]:
        self.lookup_calls += 1
        needle = credential_id.upper()
        for row in self.rows.values():
            if row.credential_id.upper() == needle:
                return row
        return None

    def get_by_user_course(self, user_sub: str, course_id: str) -> Optional[CertificateRow]:
        rid = self.by_user_course.get((user_sub, course_id))
        return self.rows.get(rid) if rid else None

    def list_for_user(self, user_sub: str) -> List[CertificateRow]:
        return [r for r in self.rows.values() if r.user_sub == user_sub]

    def list_for_course(self, course_id: str) -> List[CertificateRow]:
        return [r for r in self.rows.values() if r.course_id == course_id]

    def get_by_id(self, certificate_id: str) -> Optional[CertificateRow]:
        return self.rows.get(certificate_id)

    def revoke(
        self,
        certificate_id: str,
        *,
        revoked_by: str,
        revoked_at: datetime,
    ) -> CertificateRow:
        row = self.rows[certificate_id]
        updated = replace(
            row,
            status="revoked",
            revoked_at=revoked_at,
            revoked_by=revoked_by,
        )
        self.rows[certificate_id] = updated
        return updated


class FakeCourseAccess:
    def __init__(self) -> None:
        self.allowed: set[tuple[str, str]] = {(_STUDENT, _COURSE)}

    def is_entitled(self, user_sub: str, course_id: str) -> bool:
        return (user_sub, course_id) in self.allowed


class FakeCourseLookup:
    def __init__(self) -> None:
        self.courses: Dict[str, CourseInfo] = {
            _COURSE: CourseInfo(
                id=_COURSE,
                title="Research Methodology",
                created_by=_TEACHER,
                certificate_code=_CODE,
            ),
            _COURSE_B: CourseInfo(
                id=_COURSE_B,
                title="Other Course",
                created_by=_TEACHER,
                certificate_code="B2C8D4",
            ),
        }

    def get_course(self, course_id: str) -> Optional[CourseInfo]:
        return self.courses.get(course_id)


class FakeProfile:
    def __init__(self) -> None:
        self.names: Dict[str, tuple[str, str]] = {_STUDENT: ("Ada", "Lovelace")}

    def get_given_and_family_name(self, user_sub: str) -> tuple[str, str]:
        return self.names.get(user_sub, ("", ""))


class FakeRequirements:
    def __init__(self) -> None:
        self.by_course: Dict[str, tuple[list[QuizRequirement], list[AssignmentRequirement]]] = {
            _COURSE: (
                [QuizRequirement(module_id="m1", passed=True)],
                [
                    AssignmentRequirement(
                        assignment_id="a1",
                        status="published",
                        counts_toward_certificate=True,
                        passed=True,
                    )
                ],
            )
        }

    def get_requirements(
        self, course_id: str, user_sub: str
    ) -> tuple[Sequence[QuizRequirement], Sequence[AssignmentRequirement]]:
        return self.by_course.get(course_id, ([], []))


class FakeEntitled:
    def __init__(self) -> None:
        self.by_user: Dict[str, List[str]] = {_STUDENT: [_COURSE]}

    def list_entitled_course_ids(self, user_sub: str) -> List[str]:
        return list(self.by_user.get(user_sub, []))


def _fixed_rng(values: Sequence[int]) -> Callable[[int], int]:
    it = iter(values)

    def rng(_n: int) -> int:
        return next(it)

    return rng


def _build_service(**overrides: object):
    from services.certificates.service import CertificatesService

    kwargs = {
        "repo": FakeRepo(),
        "course_access": FakeCourseAccess(),
        "course_lookup": FakeCourseLookup(),
        "profile": FakeProfile(),
        "requirements": FakeRequirements(),
        "entitled_courses": FakeEntitled(),
        "clock": lambda: _FIXED_NOW,
        "rng": _fixed_rng([9, 12, 2, 14, 1, 0, 11, 4, 13, 8]),
    }
    kwargs.update(overrides)
    return CertificatesService(**kwargs)


def test_issued_credential_id_matches_regex() -> None:
    svc = _build_service()
    row = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert row is not None
    assert _CREDENTIAL_RE.match(row.credential_id)
    assert row.credential_id == "RS-A1B7F3-2026-9C2E10B4D8"


def test_six_hex_suffix_rejected_by_public_lookup_repo_not_called() -> None:
    repo = FakeRepo()
    svc = _build_service(repo=repo)
    with pytest.raises(BadRequest):
        svc.get_public("RS-A1B7F3-2026-9C2E10")
    assert repo.lookup_calls == 0


def test_snapshot_ignores_later_name_change() -> None:
    profile = FakeProfile()
    repo = FakeRepo()
    svc = _build_service(repo=repo, profile=profile)
    first = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert first is not None
    assert first.student_name == "Ada Lovelace"
    profile.names[_STUDENT] = ("Changed", "Name")
    again = svc.get_by_credential_id_for_test(first.credential_id)
    assert again is not None
    assert again.student_name == "Ada Lovelace"


def test_second_issue_returns_same_credential_id() -> None:
    svc = _build_service()
    first = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    second = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert first is not None and second is not None
    assert first.credential_id == second.credential_id


def test_revoke_blocks_second_row_still_one_revoked() -> None:
    repo = FakeRepo()
    svc = _build_service(repo=repo)
    issued = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert issued is not None
    svc.revoke(
        course_id=_COURSE,
        certificate_id=issued.id,
        cognito_sub=_TEACHER,
        role="teacher",
    )
    again = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert again is not None
    assert again.id == issued.id
    assert again.status == "revoked"
    assert len(repo.rows) == 1


def test_public_dict_has_no_email_and_no_user_sub() -> None:
    svc = _build_service()
    issued = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert issued is not None
    public = svc.get_public(issued.credential_id)
    assert "email" not in public
    assert "userSub" not in public
    assert public["credentialId"] == issued.credential_id
    assert public["status"] == "valid"
    assert public["studentName"] == "Ada Lovelace"
    assert public["courseTitle"] == "Research Methodology"
    assert public["issueDate"] == "September 2026"


def test_unknown_id_has_no_name() -> None:
    svc = _build_service()
    with pytest.raises(NotFound) as exc_info:
        svc.get_public("RS-A1B7F3-2026-0000000001")
    body = svc.not_found_public_body("RS-A1B7F3-2026-0000000001")
    assert body["status"] == "not_found"
    assert "studentName" not in body
    assert "name" not in body
    assert "email" not in body
    assert "userSub" not in body
    assert exc_info.value.code == "not_found"


def test_unauthenticated_me_route_does_not_call_insert() -> None:
    from services.certificates.controller import handle_certificates_request

    repo = FakeRepo()
    svc = _build_service(repo=repo)
    event = {
        "httpMethod": "GET",
        "path": "/me/certificates",
        "requestContext": {"http": {"method": "GET"}, "authorizer": {}},
    }
    resp = handle_certificates_request(event, origin="https://app.test", certificates_svc=svc)
    assert resp["statusCode"] == 401
    assert repo.insert_calls == 0


def test_other_teacher_revoke_is_403() -> None:
    svc = _build_service()
    issued = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert issued is not None
    with pytest.raises(Forbidden):
        svc.revoke(
            course_id=_COURSE,
            certificate_id=issued.id,
            cognito_sub=_OTHER_TEACHER,
            role="teacher",
        )


def test_certificate_course_mismatch_is_404() -> None:
    svc = _build_service()
    issued = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert issued is not None
    with pytest.raises(NotFound):
        svc.revoke(
            course_id=_COURSE_B,
            certificate_id=issued.id,
            cognito_sub=_TEACHER,
            role="teacher",
        )


def test_not_entitled_no_insert() -> None:
    access = FakeCourseAccess()
    access.allowed.clear()
    repo = FakeRepo()
    svc = _build_service(repo=repo, course_access=access)
    result = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert result is None
    assert repo.insert_calls == 0


def test_teacher_role_does_not_issue_without_entitlement() -> None:
    access = FakeCourseAccess()
    access.allowed.clear()
    profile = FakeProfile()
    profile.names[_TEACHER] = ("Ada", "Lovelace")
    repo = FakeRepo()
    svc = _build_service(repo=repo, course_access=access, profile=profile)
    result = svc.try_issue(user_sub=_TEACHER, course_id=_COURSE, role="teacher")
    assert result is None
    assert repo.insert_calls == 0


def test_blank_name_no_insert() -> None:
    profile = FakeProfile()
    profile.names[_STUDENT] = ("", "Lovelace")
    repo = FakeRepo()
    svc = _build_service(repo=repo, profile=profile)
    result = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert result is None
    assert repo.insert_calls == 0


def test_draft_flagged_assignment_does_not_block() -> None:
    requirements = FakeRequirements()
    requirements.by_course[_COURSE] = (
        [QuizRequirement(module_id="m1", passed=True)],
        [
            AssignmentRequirement(
                assignment_id="a-draft",
                status="draft",
                counts_toward_certificate=True,
                passed=False,
            )
        ],
    )
    svc = _build_service(requirements=requirements)
    row = svc.try_issue(user_sub=_STUDENT, course_id=_COURSE, role="student")
    assert row is not None
    assert _CREDENTIAL_RE.match(row.credential_id)
