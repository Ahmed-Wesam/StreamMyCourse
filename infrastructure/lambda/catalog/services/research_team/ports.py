"""Ports and persistence DTOs for research team (RS-14)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class RequiredCourseRow:
    course_id: str
    title: str


@dataclass(frozen=True)
class ApplicationRow:
    id: str
    user_sub: str
    status: str
    reapply_allowed: bool
    submitted_at: datetime
    full_name: str
    email: str
    country: str
    institution: str
    position: str
    publication_count: int
    project_count: int
    stats_experience: str
    sys_review_experience: str
    research_areas: tuple[str, ...]
    interests: str
    motivation: str
    weekly_hours: str
    acknowledged_at: datetime
    research_interest_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class NotifyMailMessage:
    kind: str
    to: str
    subject: str
    body: str


class ResearchTeamRepositoryPort(Protocol):
    def list_required_published_courses(self) -> List[RequiredCourseRow]:
        ...

    def set_requirement(self, course_id: str, *, required: bool) -> None:
        ...

    def is_required(self, course_id: str) -> bool:
        ...

    def course_exists(self, course_id: str) -> bool:
        ...

    def get_application(self, application_id: str) -> Optional[ApplicationRow]:
        ...

    def list_applications(self) -> List[ApplicationRow]:
        ...

    def get_latest_for_user(self, user_sub: str) -> Optional[ApplicationRow]:
        ...

    def has_accepted(self, user_sub: str) -> bool:
        ...

    def has_open(self, user_sub: str) -> bool:
        ...

    def insert_application(self, row: ApplicationRow) -> ApplicationRow:
        """Insert; raise Conflict(code=application_open) on partial unique index."""
        ...

    def update_status(self, application_id: str, status: str) -> ApplicationRow:
        ...

    def set_reapply_allowed(self, application_id: str, *, allowed: bool) -> ApplicationRow:
        ...


class CertificateLookupPort(Protocol):
    """Narrow seam over CertificatesRdsRepository.get_by_user_course."""

    def get_status_for_user_course(self, user_sub: str, course_id: str) -> Optional[str]:
        """Return certificate status or None when no row."""
        ...


class ProfileEmailPort(Protocol):
    def get_email_for_user_sub(self, user_sub: str) -> str:
        """Return users.email or empty string when missing."""
        ...


class ResearchTeamMailPort(Protocol):
    def enqueue_notify(self, message: NotifyMailMessage) -> None:
        ...


class ClockPort(Protocol):
    def __call__(self) -> datetime:
        ...
