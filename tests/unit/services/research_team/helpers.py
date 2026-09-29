"""Fakes and helpers shared by research_team unit tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from services.common.errors import Conflict
from services.research_team.ports import (
    ApplicationRow,
    NotifyMailMessage,
    RequiredCourseRow,
)
from services.research_team.service import ResearchTeamService

_NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
_COURSE_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
_COURSE_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
_STUDENT = "student-sub-1"


class FakeRepo:
    def __init__(self) -> None:
        self.required: Dict[str, RequiredCourseRow] = {}
        self.courses_exist: set[str] = set()
        self.rows: List[ApplicationRow] = []
        self.raise_open_on_insert = False

    def list_required_published_courses(self) -> List[RequiredCourseRow]:
        return list(self.required.values())

    def set_requirement(self, course_id: str, *, required: bool) -> None:
        if required:
            title = next(
                (c.title for c in self.required.values() if c.course_id == course_id),
                f"Course {course_id[:8]}",
            )
            # Prefer title from courses_exist metadata if present
            self.required[course_id] = RequiredCourseRow(course_id=course_id, title=title)
        else:
            self.required.pop(course_id, None)

    def is_required(self, course_id: str) -> bool:
        return course_id in self.required

    def course_exists(self, course_id: str) -> bool:
        return course_id in self.courses_exist

    def get_application(self, application_id: str) -> Optional[ApplicationRow]:
        for row in self.rows:
            if row.id == application_id:
                return row
        return None

    def list_applications(self) -> List[ApplicationRow]:
        return list(self.rows)

    def get_latest_for_user(self, user_sub: str) -> Optional[ApplicationRow]:
        mine = [r for r in self.rows if r.user_sub == user_sub]
        if not mine:
            return None
        return max(mine, key=lambda r: r.submitted_at)

    def has_accepted(self, user_sub: str) -> bool:
        return any(r.user_sub == user_sub and r.status == "accepted" for r in self.rows)

    def has_open(self, user_sub: str) -> bool:
        return any(
            r.user_sub == user_sub and r.status in ("submitted", "under_review")
            for r in self.rows
        )

    def insert_application(self, row: ApplicationRow) -> ApplicationRow:
        if self.raise_open_on_insert:
            raise Conflict("Application already open", code="application_open")
        if self.has_open(row.user_sub):
            raise Conflict("Application already open", code="application_open")
        self.rows.append(row)
        return row

    def update_status(self, application_id: str, status: str) -> ApplicationRow:
        for i, row in enumerate(self.rows):
            if row.id == application_id:
                updated = ApplicationRow(
                    id=row.id,
                    user_sub=row.user_sub,
                    status=status,
                    reapply_allowed=row.reapply_allowed,
                    submitted_at=row.submitted_at,
                    full_name=row.full_name,
                    email=row.email,
                    country=row.country,
                    institution=row.institution,
                    position=row.position,
                    publication_count=row.publication_count,
                    project_count=row.project_count,
                    stats_experience=row.stats_experience,
                    sys_review_experience=row.sys_review_experience,
                    research_areas=row.research_areas,
                    interests=row.interests,
                    motivation=row.motivation,
                    weekly_hours=row.weekly_hours,
                    acknowledged_at=row.acknowledged_at,
                )
                self.rows[i] = updated
                return updated
        raise Conflict("missing")

    def set_reapply_allowed(self, application_id: str, *, allowed: bool) -> ApplicationRow:
        for i, row in enumerate(self.rows):
            if row.id == application_id:
                updated = ApplicationRow(
                    id=row.id,
                    user_sub=row.user_sub,
                    status=row.status,
                    reapply_allowed=allowed,
                    submitted_at=row.submitted_at,
                    full_name=row.full_name,
                    email=row.email,
                    country=row.country,
                    institution=row.institution,
                    position=row.position,
                    publication_count=row.publication_count,
                    project_count=row.project_count,
                    stats_experience=row.stats_experience,
                    sys_review_experience=row.sys_review_experience,
                    research_areas=row.research_areas,
                    interests=row.interests,
                    motivation=row.motivation,
                    weekly_hours=row.weekly_hours,
                    acknowledged_at=row.acknowledged_at,
                )
                self.rows[i] = updated
                return updated
        raise Conflict("missing")


class FakeCertificates:
    def __init__(self) -> None:
        # (user_sub, course_id) -> status
        self.statuses: Dict[tuple[str, str], str] = {}

    def get_status_for_user_course(self, user_sub: str, course_id: str) -> Optional[str]:
        return self.statuses.get((user_sub, course_id))


class FakeProfile:
    def __init__(self, email: str = "profile@example.com") -> None:
        self.email = email

    def get_email_for_user_sub(self, user_sub: str) -> str:
        return self.email


class FakeMail:
    def __init__(self) -> None:
        self.messages: List[NotifyMailMessage] = []
        self.raise_on_enqueue = False

    def enqueue_notify(self, message: NotifyMailMessage) -> None:
        if self.raise_on_enqueue:
            raise RuntimeError("sqs down")
        self.messages.append(message)


def make_service(
    *,
    repo: Optional[FakeRepo] = None,
    certs: Optional[FakeCertificates] = None,
    profile: Optional[FakeProfile] = None,
    mail: Optional[FakeMail] = None,
) -> tuple[ResearchTeamService, FakeRepo, FakeCertificates, FakeProfile, FakeMail]:
    repo = repo or FakeRepo()
    certs = certs or FakeCertificates()
    profile = profile or FakeProfile()
    mail = mail or FakeMail()
    svc = ResearchTeamService(repo, certs, profile, mail, clock=lambda: _NOW)
    return svc, repo, certs, profile, mail


def valid_submit_body(**overrides) -> dict:
    body = {
        "fullName": "Ada Lovelace",
        "country": "Jordan",
        "institution": "RS University",
        "position": "Medical Student",
        "publicationCount": 1,
        "projectCount": 2,
        "statsExperience": "Beginner",
        "sysReviewExperience": "None",
        "researchAreas": ["Clinical Research"],
        "interests": "Meta-analysis",
        "motivation": "I want to contribute to research.",
        "weeklyHours": "5–10 hours/week",
        "acknowledgement": True,
    }
    body.update(overrides)
    return body


def make_app_row(
    *,
    user_sub: str = _STUDENT,
    status: str = "submitted",
    reapply_allowed: bool = False,
    submitted_at: Optional[datetime] = None,
    email: str = "profile@example.com",
) -> ApplicationRow:
    now = submitted_at or _NOW
    return ApplicationRow(
        id=str(uuid4()),
        user_sub=user_sub,
        status=status,
        reapply_allowed=reapply_allowed,
        submitted_at=now,
        full_name="Ada Lovelace",
        email=email,
        country="Jordan",
        institution="RS University",
        position="Medical Student",
        publication_count=1,
        project_count=2,
        stats_experience="Beginner",
        sys_review_experience="None",
        research_areas=("Clinical Research",),
        interests="Meta-analysis",
        motivation="I want to contribute to research.",
        weekly_hours="5–10 hours/week",
        acknowledged_at=now,
    )
