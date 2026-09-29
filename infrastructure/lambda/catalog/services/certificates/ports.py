"""Ports and persistence DTOs for certificates (RS-12)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Protocol, Sequence

from services.certificates.eligibility import AssignmentRequirement, QuizRequirement


@dataclass(frozen=True)
class CertificateRow:
    id: str
    user_sub: str
    course_id: str
    credential_id: str
    student_name: str
    course_title: str
    issue_date: date
    instructor_name: str
    instructor_title: str
    status: str
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None


@dataclass(frozen=True)
class CourseInfo:
    id: str
    title: str
    created_by: str
    certificate_code: str


class CertificatesRepositoryPort(Protocol):
    def insert_certificate(self, row: CertificateRow) -> CertificateRow:
        """Insert or, on unique (user_sub, course_id), return the existing row."""
        ...

    def get_by_credential_id(self, credential_id: str) -> Optional[CertificateRow]:
        ...

    def get_by_user_course(self, user_sub: str, course_id: str) -> Optional[CertificateRow]:
        ...

    def list_for_user(self, user_sub: str) -> List[CertificateRow]:
        ...

    def list_for_course(self, course_id: str) -> List[CertificateRow]:
        ...

    def get_by_id(self, certificate_id: str) -> Optional[CertificateRow]:
        ...

    def revoke(
        self,
        certificate_id: str,
        *,
        revoked_by: str,
        revoked_at: datetime,
    ) -> CertificateRow:
        ...


class CourseAccessPort(Protocol):
    def is_entitled(self, user_sub: str, course_id: str) -> bool:
        """Paid course purchase or paid bundle of a published course. Role is not an input."""
        ...


class CourseLookupPort(Protocol):
    def get_course(self, course_id: str) -> Optional[CourseInfo]:
        ...


class UserProfilePort(Protocol):
    def get_given_and_family_name(self, user_sub: str) -> tuple[str, str]:
        """Return (given_name, family_name); either may be blank."""
        ...


class RequirementsPort(Protocol):
    def get_requirements(
        self, course_id: str, user_sub: str
    ) -> tuple[Sequence[QuizRequirement], Sequence[AssignmentRequirement]]:
        """Visible quizzes and assignments (caller may include drafts; eligibility filters)."""
        ...


class EntitledCoursesPort(Protocol):
    def list_entitled_course_ids(self, user_sub: str) -> List[str]:
        ...
