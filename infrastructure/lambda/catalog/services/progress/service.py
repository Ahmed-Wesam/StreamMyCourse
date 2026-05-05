from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.common.errors import BadRequest, Forbidden, NotFound, ServiceUnavailable, Unauthorized
from services.course_management.models import Course, Lesson
from services.course_management.ports import CourseCatalogRepositoryPort
from services.enrollment.ports import EnrollmentRepositoryPort
from services.progress.ports import LessonProgressRepositoryPort, LessonProgressRow


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class LessonProgressService:
    def __init__(
        self,
        course_repo: CourseCatalogRepositoryPort,
        enrollments: EnrollmentRepositoryPort,
        progress_repo: LessonProgressRepositoryPort,
        *,
        complete_ratio: float,
        position_slack_sec: int,
        min_put_interval_sec: int = 0,
    ) -> None:
        self._courses = course_repo
        self._enrollments = enrollments
        self._progress = progress_repo
        self._complete_ratio = complete_ratio
        self._slack = max(0, position_slack_sec)
        self._min_interval = max(0, min_put_interval_sec)
        self._last_put_ts: Dict[tuple[str, str], float] = {}

    def _same_access_as_lesson_list(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> Course:
        course = self._courses.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if auth_enforced and course.status == "DRAFT":
            if not self._can_manage_course(course, cognito_sub=cognito_sub, role=role):
                raise NotFound("Course not found")
        return course

    @staticmethod
    def _norm_role(role: str) -> str:
        return (role or "").strip().lower()

    def _is_admin(self, role: str) -> bool:
        return self._norm_role(role) == "admin"

    def _teacher_or_admin(self, role: str) -> bool:
        return self._norm_role(role) in ("teacher", "admin")

    def _can_manage_course(self, course: Course, *, cognito_sub: str, role: str) -> bool:
        if self._is_admin(role):
            return True
        if not self._teacher_or_admin(role):
            return False
        owner = (course.createdBy or "").strip()
        if not owner:
            return True
        return owner == cognito_sub.strip()

    def enrolled_or_staff(self, course: Course, *, course_id: str, cognito_sub: str, role: str) -> bool:
        if self._can_manage_course(course, cognito_sub=cognito_sub, role=role):
            return True
        if course.status != "PUBLISHED":
            return False
        return self._enrollments.has_enrollment(user_sub=cognito_sub, course_id=course_id)

    def get_course_progress(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> Dict[str, Any]:
        if not auth_enforced:
            raise ServiceUnavailable(
                "Lesson progress requires Cognito authorizer on API Gateway.",
                code="auth_not_configured",
            )
        if not cognito_sub.strip():
            raise Unauthorized("Authentication required", code="forbidden")

        course = self._same_access_as_lesson_list(
            course_id, cognito_sub=cognito_sub, role=role, auth_enforced=auth_enforced
        )
        if not self.enrolled_or_staff(course, course_id=course_id, cognito_sub=cognito_sub, role=role):
            raise Forbidden("Enrollment required to view this course", code="enrollment_required")

        lessons = sorted(self._courses.list_lessons(course_id), key=lambda x: x.order)
        ready = [l for l in lessons if (l.videoStatus or "").strip().lower() == "ready"]
        total_ready = len(ready)
        stored = {r.lesson_id: r for r in self._progress.list_for_course(user_sub=cognito_sub, course_id=course_id)}
        lesson_payloads: List[Dict[str, Any]] = []
        completed_count = 0
        for lesson in lessons:
            if (lesson.videoStatus or "").strip().lower() != "ready":
                continue
            row = stored.get(lesson.id)
            completed = bool(row and row.completed)
            if completed:
                completed_count += 1
            lesson_payloads.append(
                {
                    "lessonId": lesson.id,
                    "completed": completed,
                    "completedAt": row.completed_at_iso if row else None,
                    "lastPositionSec": int(row.last_position_sec) if row else 0,
                }
            )

        pct = 0.0
        if total_ready > 0:
            pct = round(100.0 * completed_count / total_ready, 2)

        return {
            "courseId": course_id,
            "totalReadyLessons": total_ready,
            "completedCount": completed_count,
            "percentComplete": pct,
            "lessons": lesson_payloads,
        }

    def update_lesson_progress(
        self,
        course_id: str,
        lesson_id: str,
        *,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
        last_position_sec: Optional[int],
        mark_complete: bool,
        mark_incomplete: bool,
        now_ts: float,
    ) -> Dict[str, Any]:
        if not auth_enforced:
            raise ServiceUnavailable(
                "Lesson progress requires Cognito authorizer on API Gateway.",
                code="auth_not_configured",
            )
        if not cognito_sub.strip():
            raise Unauthorized("Authentication required", code="forbidden")
        if mark_complete and mark_incomplete:
            raise BadRequest("markComplete and markIncomplete cannot both be true", code="bad_request")
        course = self._same_access_as_lesson_list(
            course_id, cognito_sub=cognito_sub, role=role, auth_enforced=auth_enforced
        )
        if not self.enrolled_or_staff(course, course_id=course_id, cognito_sub=cognito_sub, role=role):
            raise Forbidden("Enrollment required to view this course", code="enrollment_required")

        lesson = self._courses.get_lesson_by_id(course_id, lesson_id)
        if not lesson:
            raise NotFound("Lesson not found")

        rows = self._progress.list_for_course(user_sub=cognito_sub, course_id=course_id)
        by_lesson = {r.lesson_id: r for r in rows}
        current = by_lesson.get(lesson_id)
        completed = bool(current.completed) if current else False
        completed_at_iso = current.completed_at_iso if current else None
        position = int(current.last_position_sec) if current else 0

        if last_position_sec is not None:
            if self._min_interval > 0:
                key = (cognito_sub, lesson_id)
                prev = self._last_put_ts.get(key, 0.0)
                if now_ts - prev < self._min_interval:
                    return {"ok": True, "throttled": True}
                self._last_put_ts[key] = now_ts
            new_pos = int(last_position_sec)
            if new_pos < 0:
                raise BadRequest("lastPositionSec must be non-negative", code="bad_request")
            dur = int(lesson.duration or 0)
            if dur > 0:
                cap = dur + self._slack
                if new_pos > cap:
                    new_pos = cap
            position = new_pos

        if mark_incomplete:
            completed = False
            completed_at_iso = None

        if mark_complete:
            completed = True
            if not completed_at_iso:
                completed_at_iso = _utc_now_iso()
        elif (
            not mark_incomplete
            and not completed
            and lesson.duration > 0
            and position / float(lesson.duration) >= self._complete_ratio
        ):
            completed = True
            completed_at_iso = _utc_now_iso()

        self._progress.upsert(
            user_sub=cognito_sub,
            course_id=course_id,
            lesson_id=lesson_id,
            last_position_sec=position,
            completed=completed,
            completed_at_iso=completed_at_iso,
        )
        return {"ok": True, "throttled": False}
