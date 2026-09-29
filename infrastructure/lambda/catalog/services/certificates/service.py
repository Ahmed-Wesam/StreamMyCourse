"""Certificates domain service (RS-12): issue, verify, list, revoke."""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Callable, List, Optional, Sequence
from uuid import UUID, uuid4

from services.certificates.contracts import (
    CertificateMineItem,
    CertificatePublicItem,
    CourseCertificateItem,
    InProgressItem,
    ListCourseCertificatesResponse,
    MeCertificatesResponse,
    NotFoundPublicBody,
    ProfileIncompleteItem,
    RevokeResponse,
)
from services.certificates.credential_id import (
    format_issue_label,
    generate_credential_id,
    is_valid_credential_id,
    normalize_credential_id,
)
from services.certificates.eligibility import (
    AssignmentRequirement,
    QuizRequirement,
    is_course_eligible,
)
from services.certificates.models import (
    INSTRUCTOR_NAME,
    INSTRUCTOR_TITLE,
    PROFILE_HREF,
    PROFILE_INCOMPLETE_MESSAGE,
)
from services.certificates.ports import (
    CertificateRow,
    CertificatesRepositoryPort,
    CourseAccessPort,
    CourseInfo,
    CourseLookupPort,
    EntitledCoursesPort,
    RequirementsPort,
    UserProfilePort,
)
from services.common.errors import BadRequest, Forbidden, NotFound

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]
Rng = Callable[[int], int]


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
    except Exception:
        return False
    return True


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


def _compose_student_name(given: str, family: str) -> Optional[str]:
    g = (given or "").strip()
    f = (family or "").strip()
    if not g or not f:
        return None
    return f"{g} {f}"


def _requirement_counts(
    quizzes: Sequence[QuizRequirement],
    assignments: Sequence[AssignmentRequirement],
) -> tuple[int, int]:
    """passedCount / totalCount of visible quizzes + published flagged assignments."""
    required_assignments = [
        a
        for a in assignments
        if a.status == "published" and a.counts_toward_certificate
    ]
    total = len(quizzes) + len(required_assignments)
    passed = sum(1 for q in quizzes if q.passed) + sum(
        1 for a in required_assignments if a.passed
    )
    return passed, total


class CertificatesService:
    def __init__(
        self,
        repo: CertificatesRepositoryPort,
        course_access: CourseAccessPort,
        course_lookup: CourseLookupPort,
        profile: UserProfilePort,
        requirements: RequirementsPort,
        entitled_courses: EntitledCoursesPort,
        *,
        clock: Clock | None = None,
        rng: Rng | None = None,
    ) -> None:
        self._repo = repo
        self._course_access = course_access
        self._course_lookup = course_lookup
        self._profile = profile
        self._requirements = requirements
        self._entitled = entitled_courses
        self._clock = clock or _default_clock
        self._rng = rng or secrets.randbelow

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now

    def _get_course(self, course_id: str) -> CourseInfo:
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        course = self._course_lookup.get_course(course_id)
        if course is None:
            raise NotFound("Course not found")
        return course

    def _can_manage_course(self, course: CourseInfo, *, cognito_sub: str, role: str) -> bool:
        sub = (cognito_sub or "").strip()
        r = (role or "").strip().lower()
        if not sub:
            return False
        if r == "admin":
            return True
        if r != "teacher":
            return False
        owner = (course.created_by or "").strip()
        return bool(owner) and owner == sub

    def _ensure_can_manage(self, course_id: str, *, cognito_sub: str, role: str) -> CourseInfo:
        course = self._get_course(course_id)
        r = (role or "").strip().lower()
        if r == "admin":
            return course
        if r not in ("teacher", "admin"):
            raise Forbidden("Teacher or admin role required")
        if not self._can_manage_course(course, cognito_sub=cognito_sub, role=role):
            raise Forbidden("Not allowed to manage this course")
        return course

    def _row_to_public(self, row: CertificateRow) -> CertificatePublicItem:
        return {
            "credentialId": row.credential_id,
            "status": row.status,
            "studentName": row.student_name,
            "courseTitle": row.course_title,
            "issueDate": format_issue_label(row.issue_date),
        }

    def _row_to_mine(self, row: CertificateRow) -> CertificateMineItem:
        return {
            "id": row.id,
            "credentialId": row.credential_id,
            "status": row.status,
            "studentName": row.student_name,
            "courseTitle": row.course_title,
            "issueDate": format_issue_label(row.issue_date),
            "instructorName": row.instructor_name,
            "instructorTitle": row.instructor_title,
            "courseId": row.course_id,
        }

    def not_found_public_body(self, credential_id: str = "") -> NotFoundPublicBody:
        body: NotFoundPublicBody = {"status": "not_found"}
        if credential_id:
            body["credentialId"] = normalize_credential_id(credential_id)
        return body

    def get_public(self, credential_id: str) -> CertificatePublicItem:
        raw = (credential_id or "").strip()
        if not is_valid_credential_id(raw):
            raise BadRequest("Invalid credential id", code="invalid_credential_id")
        row = self._repo.get_by_credential_id(normalize_credential_id(raw))
        if row is None:
            raise NotFound("Certificate not found", code="not_found")
        return self._row_to_public(row)

    def get_by_credential_id_for_test(self, credential_id: str) -> Optional[CertificateRow]:
        """Test helper: return the stored row without HTTP shaping."""
        return self._repo.get_by_credential_id(normalize_credential_id(credential_id))

    def try_issue(
        self,
        *,
        user_sub: str,
        course_id: str,
        role: str,
    ) -> Optional[CertificateRow]:
        """Issue when entitled + eligible + name complete; else return existing or None.

        Does not revoke when requirements tighten after issuance. Unique insert
        collision returns the existing row. Revoked rows are never reissued.

        ``role`` is accepted so quiz, grade, and profile hooks keep one signature.
        Entitlement does not use it: teacher or admin ownership is not a purchase.
        """
        sub = (user_sub or "").strip()
        if not sub or not _is_valid_uuid(course_id):
            return None

        existing = self._repo.get_by_user_course(sub, course_id)
        if existing is not None:
            return existing

        if not self._course_access.is_entitled(sub, course_id):
            return None

        course = self._course_lookup.get_course(course_id)
        if course is None:
            return None

        quizzes, assignments = self._requirements.get_requirements(course_id, sub)
        if not is_course_eligible(quizzes=quizzes, assignments=assignments):
            return None

        given, family = self._profile.get_given_and_family_name(sub)
        student_name = _compose_student_name(given, family)
        if student_name is None:
            return None

        now = self._now()
        credential_id = generate_credential_id(
            course_certificate_code=course.certificate_code,
            now=now,
            rng=self._rng,
        )
        row = CertificateRow(
            id=str(uuid4()),
            user_sub=sub,
            course_id=course_id,
            credential_id=credential_id,
            student_name=student_name,
            course_title=course.title,
            issue_date=now.date(),
            instructor_name=INSTRUCTOR_NAME,
            instructor_title=INSTRUCTOR_TITLE,
            status="valid",
        )
        return self._repo.insert_certificate(row)

    def try_issue_for_user(self, *, user_sub: str, role: str) -> None:
        """Attempt issuance for every entitled course (profile-completion hook)."""
        sub = (user_sub or "").strip()
        if not sub:
            return
        for course_id in self._entitled.list_entitled_course_ids(sub):
            self.try_issue(user_sub=sub, course_id=course_id, role=role)

    def list_mine(self, *, user_sub: str, role: str) -> MeCertificatesResponse:
        sub = (user_sub or "").strip()
        entitled_ids = self._entitled.list_entitled_course_ids(sub)

        for course_id in entitled_ids:
            self.try_issue(user_sub=sub, course_id=course_id, role=role)

        certificates = [self._row_to_mine(r) for r in self._repo.list_for_user(sub)]
        issued_course_ids = {c["courseId"] for c in certificates}

        in_progress: List[InProgressItem] = []
        profile_incomplete: List[ProfileIncompleteItem] = []

        given, family = self._profile.get_given_and_family_name(sub)
        name_ok = _compose_student_name(given, family) is not None

        for course_id in entitled_ids:
            if course_id in issued_course_ids:
                continue
            course = self._course_lookup.get_course(course_id)
            if course is None:
                continue
            quizzes, assignments = self._requirements.get_requirements(course_id, sub)
            passed, total = _requirement_counts(quizzes, assignments)
            if total == 0:
                continue
            eligible = is_course_eligible(quizzes=quizzes, assignments=assignments)
            if eligible and not name_ok:
                profile_incomplete.append(
                    {
                        "courseId": course_id,
                        "courseTitle": course.title,
                        "requirementsMet": True,
                        "message": PROFILE_INCOMPLETE_MESSAGE,
                        "href": PROFILE_HREF,
                    }
                )
                continue
            if not eligible:
                in_progress.append(
                    {
                        "courseId": course_id,
                        "courseTitle": course.title,
                        "passedCount": passed,
                        "totalCount": total,
                    }
                )

        return {
            "certificates": certificates,
            "inProgress": in_progress,
            "profileIncomplete": profile_incomplete,
        }

    def list_for_course(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> ListCourseCertificatesResponse:
        self._ensure_can_manage(course_id, cognito_sub=cognito_sub, role=role)
        items: List[CourseCertificateItem] = []
        for row in self._repo.list_for_course(course_id):
            items.append(
                {
                    "id": row.id,
                    "credentialId": row.credential_id,
                    "status": row.status,
                    "studentName": row.student_name,
                    "courseTitle": row.course_title,
                    "issueDate": format_issue_label(row.issue_date),
                }
            )
        return {"certificates": items}

    def revoke(
        self,
        course_id: str,
        certificate_id: str,
        *,
        cognito_sub: str,
        role: str,
    ) -> RevokeResponse:
        self._ensure_can_manage(course_id, cognito_sub=cognito_sub, role=role)
        if not _is_valid_uuid(certificate_id):
            raise NotFound("Certificate not found")
        row = self._repo.get_by_id(certificate_id)
        if row is None or row.course_id != course_id:
            raise NotFound("Certificate not found")
        if row.status == "revoked":
            return {
                "id": row.id,
                "credentialId": row.credential_id,
                "status": row.status,
            }
        updated = self._repo.revoke(
            certificate_id,
            revoked_by=(cognito_sub or "").strip(),
            revoked_at=self._now(),
        )
        return {
            "id": updated.id,
            "credentialId": updated.credential_id,
            "status": updated.status,
        }
