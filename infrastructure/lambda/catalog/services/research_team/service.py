"""Research team applications domain service (RS-14)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

from services.common.errors import BadRequest, Conflict, Forbidden, NotFound
from services.research_team.contracts import (
    MeCourseItem,
    MeResearchTeamResponse,
    application_to_admin_json,
    application_to_json,
    parse_patch_status,
    parse_requirement_body,
    parse_submit_body,
    strip_crlf,
)
from services.research_team.models import (
    BODY_REAPPLY,
    BODY_STATUS_CHANGE,
    BODY_SUBMITTED,
    OPEN_STATUSES,
    SUBJECT_REAPPLY,
    SUBJECT_STATUS_CHANGE,
    SUBJECT_SUBMITTED,
)
from services.research_team.ports import (
    ApplicationRow,
    CertificateLookupPort,
    ClockPort,
    NotifyMailMessage,
    ProfileEmailPort,
    ResearchTeamMailPort,
    ResearchTeamRepositoryPort,
)

logger = logging.getLogger(__name__)


def _default_clock() -> datetime:
    return datetime.now(timezone.utc)


class ResearchTeamService:
    def __init__(
        self,
        repo: ResearchTeamRepositoryPort,
        certificates: CertificateLookupPort,
        profile_email: ProfileEmailPort,
        mail: ResearchTeamMailPort,
        *,
        clock: Optional[ClockPort] = None,
    ) -> None:
        self._repo = repo
        self._certificates = certificates
        self._profile_email = profile_email
        self._mail = mail
        self._clock = clock or _default_clock

    def _require_admin(self, role: str) -> None:
        if (role or "").strip().lower() != "admin":
            raise Forbidden("Admin role required")

    def _eligibility_snapshot(self, user_sub: str) -> tuple[List[MeCourseItem], bool]:
        required = self._repo.list_required_published_courses()
        courses: List[MeCourseItem] = []
        if not required:
            return courses, False
        all_met = True
        for row in required:
            status = self._certificates.get_status_for_user_course(user_sub, row.course_id)
            certified = status == "valid"
            if not certified:
                all_met = False
            courses.append(
                {
                    "courseId": row.course_id,
                    "title": row.title,
                    "certified": certified,
                }
            )
        return courses, all_met

    def _can_submit(
        self,
        *,
        eligible: bool,
        latest: Optional[ApplicationRow],
        has_accepted: bool,
        has_open: bool,
    ) -> bool:
        if not eligible or has_open or has_accepted:
            return False
        if latest is None:
            return True
        return latest.status == "rejected" and latest.reapply_allowed

    def get_requirements(self) -> Dict[str, Any]:
        rows = self._repo.list_required_published_courses()
        return {
            "courses": [{"id": r.course_id, "title": r.title} for r in rows],
        }

    def set_requirement(
        self, course_id: str, body: Mapping[str, Any], *, role: str
    ) -> Dict[str, Any]:
        self._require_admin(role)
        required = parse_requirement_body(body)
        if not self._repo.course_exists(course_id):
            raise NotFound("Course not found")
        self._repo.set_requirement(course_id, required=required)
        return {"courseId": course_id, "required": required}

    def get_requirement(self, course_id: str, *, role: str) -> Dict[str, Any]:
        self._require_admin(role)
        if not self._repo.course_exists(course_id):
            raise NotFound("Course not found")
        return {
            "courseId": course_id,
            "required": self._repo.is_required(course_id),
        }

    def get_me(self, *, user_sub: str, role: str) -> MeResearchTeamResponse:
        if (role or "").strip().lower() != "student":
            raise Forbidden("Student role required")
        courses, eligible = self._eligibility_snapshot(user_sub)
        latest = self._repo.get_latest_for_user(user_sub)
        has_accepted = self._repo.has_accepted(user_sub)
        has_open = self._repo.has_open(user_sub)
        can_submit = self._can_submit(
            eligible=eligible,
            latest=latest,
            has_accepted=has_accepted,
            has_open=has_open,
        )
        return {
            "courses": courses,
            "eligible": eligible,
            "canSubmit": can_submit,
            "application": application_to_json(latest) if latest else None,
        }

    def submit(self, body: Mapping[str, Any], *, user_sub: str, role: str) -> Dict[str, Any]:
        if (role or "").strip().lower() != "student":
            raise Forbidden("Student role required")
        parsed = parse_submit_body(body)
        _, eligible = self._eligibility_snapshot(user_sub)
        if not eligible:
            raise Forbidden("Not eligible to apply", code="not_eligible")

        if self._repo.has_accepted(user_sub):
            raise Conflict("Already accepted", code="already_accepted")
        if self._repo.has_open(user_sub):
            raise Conflict("Application already open", code="application_open")

        latest = self._repo.get_latest_for_user(user_sub)
        if latest is not None:
            if latest.status == "rejected" and not latest.reapply_allowed:
                raise Conflict("Reapply not allowed", code="reapply_not_allowed")
            if latest.status != "rejected":
                # Defensive: non-open non-rejected should be accepted (handled above)
                # or an unexpected state.
                if latest.status in OPEN_STATUSES:
                    raise Conflict("Application already open", code="application_open")

        email = strip_crlf((self._profile_email.get_email_for_user_sub(user_sub) or "").strip())
        if not email:
            raise BadRequest("Account email is required", code="email_required")
        now = self._clock()
        row = ApplicationRow(
            id=str(uuid4()),
            user_sub=user_sub,
            status="submitted",
            reapply_allowed=False,
            submitted_at=now,
            full_name=parsed["full_name"],
            email=email,
            country=parsed["country"],
            institution=parsed["institution"],
            position=parsed["position"],
            publication_count=parsed["publication_count"],
            project_count=parsed["project_count"],
            stats_experience=parsed["stats_experience"],
            sys_review_experience=parsed["sys_review_experience"],
            research_areas=parsed["research_areas"],
            interests=parsed["interests"],
            motivation=parsed["motivation"],
            weekly_hours=parsed["weekly_hours"],
            acknowledged_at=now,
        )
        inserted = self._repo.insert_application(row)
        self._try_notify(
            to=email,
            subject=SUBJECT_SUBMITTED,
            body=BODY_SUBMITTED,
            context="submit",
            application_id=inserted.id,
        )
        return application_to_json(inserted)

    def list_applications(self, *, role: str) -> Dict[str, Any]:
        self._require_admin(role)
        rows = self._repo.list_applications()
        return {"applications": [application_to_admin_json(r) for r in rows]}

    def get_application(self, application_id: str, *, role: str) -> Dict[str, Any]:
        self._require_admin(role)
        row = self._repo.get_application(application_id)
        if row is None:
            raise NotFound("Application not found")
        return application_to_admin_json(row)

    def patch_application(
        self, application_id: str, body: Mapping[str, Any], *, role: str
    ) -> Dict[str, Any]:
        self._require_admin(role)
        # Ignore reapplyAllowed if present.
        status = parse_patch_status(body)
        row = self._repo.get_application(application_id)
        if row is None:
            raise NotFound("Application not found")
        if row.status == "accepted":
            raise Conflict("Accepted applications cannot be changed", code="already_accepted")
        if row.status == status:
            return application_to_admin_json(row)

        # Admin may patch a rejected row to under_review or accepted (mistake fix).
        # Also allow normal transitions from submitted/under_review.
        if row.status == "rejected" and status not in ("under_review", "accepted", "rejected"):
            raise BadRequest("Invalid status transition")

        # One accepted and one open per student — reject before the unique indexes fire.
        if status == "accepted":
            if self._repo.has_accepted(row.user_sub):
                raise Conflict("Student already accepted", code="already_accepted")
            # Accepting a rejected row while another application is still open.
            if row.status not in OPEN_STATUSES and self._repo.has_open(row.user_sub):
                raise Conflict(
                    "Close the open application before accepting another",
                    code="application_open",
                )
        if status in OPEN_STATUSES and row.status not in OPEN_STATUSES:
            if self._repo.has_open(row.user_sub):
                raise Conflict("Application already open", code="application_open")

        updated = self._repo.update_status(application_id, status)
        self._try_notify(
            to=updated.email,
            subject=SUBJECT_STATUS_CHANGE,
            body=BODY_STATUS_CHANGE,
            context="status_change",
            application_id=updated.id,
        )
        return application_to_admin_json(updated)

    def allow_reapply(self, application_id: str, *, role: str) -> Dict[str, Any]:
        self._require_admin(role)
        row = self._repo.get_application(application_id)
        if row is None:
            raise NotFound("Application not found")
        latest = self._repo.get_latest_for_user(row.user_sub)
        if latest is None or latest.id != row.id:
            raise Conflict("Not the latest application", code="not_latest")
        if row.status != "rejected":
            raise Conflict("Application is not rejected", code="not_rejected")
        if self._repo.has_accepted(row.user_sub):
            raise Conflict("Student already accepted", code="already_accepted")
        updated = self._repo.set_reapply_allowed(application_id, allowed=True)
        self._try_notify(
            to=updated.email,
            subject=SUBJECT_REAPPLY,
            body=BODY_REAPPLY,
            context="allow_reapply",
            application_id=updated.id,
        )
        return application_to_admin_json(updated)

    def _try_notify(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        context: str,
        application_id: str,
    ) -> None:
        to_addr = (to or "").strip()
        if not to_addr:
            logger.info(
                "Research team notify skipped: empty email",
                extra={"context": context, "application_id": application_id},
            )
            return
        try:
            self._mail.enqueue_notify(
                NotifyMailMessage(
                    kind="notify",
                    to=to_addr,
                    subject=subject,
                    body=strip_crlf(body),
                )
            )
        except Exception:
            logger.exception(
                "Research team notify enqueue failed",
                extra={"context": context, "application_id": application_id},
            )
