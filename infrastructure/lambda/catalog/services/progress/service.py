"""Lesson Progress Service — domain logic for tracking lesson completion.

This module implements the LessonProgressService which handles:
- Authorization (enrollment or course ownership)
- Auto-completion based on position/duration ratio
- Position validation with configurable slack
- Explicit mark complete/incomplete actions
- Course-level progress aggregation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import UUID

from services.common.errors import BadRequest, Forbidden, NotFound
from services.progress.contracts import (
    CourseProgressResponse,
    LessonProgressItem,
    UpdateProgressResponse,
)
from services.progress.ports import LessonProgressRepositoryPort, LessonProgressRow

if TYPE_CHECKING:
    from services.course_management.ports import CourseCatalogRepositoryPort
    from services.enrollment.ports import EnrollmentRepositoryPort


logger = logging.getLogger(__name__)


def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except Exception:
        return False


class LessonProgressService:
    """Service for managing lesson progress.

    Args:
        progress_repo: Repository for lesson progress persistence
        enrollment_repo: Repository for enrollment checks
        course_repo: Repository for course data (to check ownership)
        progress_complete_ratio: Ratio of position/duration to auto-complete (e.g., 0.92)
        position_slack_sec: Allowed slack for position beyond duration (e.g., 30 seconds)
    """

    def __init__(
        self,
        progress_repo: LessonProgressRepositoryPort,
        enrollment_repo: "EnrollmentRepositoryPort",
        course_repo: "CourseCatalogRepositoryPort",
        progress_complete_ratio: float = 0.92,
        position_slack_sec: int = 30,
    ):
        self._progress_repo = progress_repo
        self._enrollment_repo = enrollment_repo
        self._course_repo = course_repo
        self._progress_complete_ratio = progress_complete_ratio
        self._position_slack_sec = position_slack_sec

    def _check_authorization(self, user_sub: str, course_id: str) -> bool:
        """Check if user is authorized to access course progress.

        Authorization is granted if:
        - User is enrolled in the course, OR
        - User is the course owner (teacher)

        Returns:
            True if authorized, False otherwise
        """
        # Check enrollment first
        if self._enrollment_repo.has_enrollment(user_sub=user_sub, course_id=course_id):
            return True

        # Check if user is the course owner
        course = self._course_repo.get_course(course_id)
        if course and course.createdBy == user_sub:
            return True

        return False

    def _compute_auto_complete(self, position: int, duration: int) -> bool:
        """Compute whether lesson should be auto-completed based on position/duration ratio.

        Args:
            position: Current playback position in seconds
            duration: Total lesson duration in seconds

        Returns:
            True if position/duration >= progress_complete_ratio
        """
        if duration <= 0:
            return False
        return (position / duration) >= self._progress_complete_ratio

    def _validate_position(self, position: int, duration: int) -> None:
        """Validate that position is within acceptable bounds.

        Args:
            position: Current playback position in seconds
            duration: Total lesson duration in seconds (0 = unknown client-side)

        Raises:
            BadRequest: If position > duration + position_slack_sec when duration > 0
        """
        if duration <= 0:
            # Client may send duration=0 before video metadata or lesson length is available.
            # Using duration + slack would cap position at ~30s and reject legitimate playback.
            return
        max_allowed = duration + self._position_slack_sec
        if position > max_allowed:
            raise BadRequest(
                f"Position ({position}) exceeds maximum allowed ({max_allowed} = duration + {self._position_slack_sec} seconds slack)",
                code="invalid_position",
            )

    def get_course_progress(
        self,
        user_sub: str,
        course_id: str,
    ) -> CourseProgressResponse:
        """Get aggregated progress for a course.

        Args:
            user_sub: User identifier (Cognito sub)
            course_id: Course identifier

        Returns:
            CourseProgressResponse with totals and per-lesson progress

        Raises:
            Forbidden: If user is not enrolled and not course owner
        """
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")

        if not self._check_authorization(user_sub, course_id):
            raise Forbidden(
                "Enrollment required to view course progress",
                code="enrollment_required",
            )

        # Get all lessons in the course
        all_lessons = self._course_repo.list_lessons(course_id)

        # Get user's progress records for this course
        progress_rows = self._progress_repo.get_progress_for_course(
            user_sub=user_sub,
            course_id=course_id,
        )

        known_lesson_ids = {l.id for l in all_lessons}
        drift = [r.lesson_id for r in progress_rows if r.lesson_id not in known_lesson_ids]
        if drift:
            logger.info(
                "Drifted lesson_progress rows ignored",
                extra={"course_id": course_id, "drift_count": len(drift)},
            )

        # Create lookup dict for progress by lesson_id
        progress_by_lesson: Dict[str, LessonProgressRow] = {
            row.lesson_id: row for row in progress_rows
        }

        # Build progress list for all lessons (merging with progress data)
        lessons: List[LessonProgressItem] = []
        completed_count = 0

        for lesson in all_lessons:
            row = progress_by_lesson.get(lesson.id)
            if row:
                item: LessonProgressItem = {
                    "lessonId": row.lesson_id,
                    "completed": row.completed,
                    "lastPositionSec": row.last_position_sec,
                }
                if row.completed and row.completed_at:
                    item["completedAt"] = row.completed_at.isoformat()
                if row.completed:
                    completed_count += 1
            else:
                # No progress record yet - return default "not started" state
                item = {
                    "lessonId": lesson.id,
                    "completed": False,
                    "lastPositionSec": 0,
                }
            lessons.append(item)

        total_lessons = len(all_lessons)
        percent_complete = 0.0
        if total_lessons > 0:
            percent_complete = round((completed_count / total_lessons) * 100, 2)

        return {
            "courseId": course_id,
            "totalReadyLessons": total_lessons,
            "completedCount": completed_count,
            "percentComplete": percent_complete,
            "lessons": lessons,
        }

    def update_lesson_progress(
        self,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        position: int,
        duration: int,
        mark_complete: bool = False,
        mark_incomplete: bool = False,
    ) -> UpdateProgressResponse:
        """Update progress for a specific lesson.

        Args:
            user_sub: User identifier (Cognito sub)
            course_id: Course identifier
            lesson_id: Lesson identifier
            position: Current playback position in seconds
            duration: Total lesson duration in seconds
            mark_complete: Explicitly mark lesson as complete (overrides auto-complete)
            mark_incomplete: Explicitly mark lesson as incomplete

        Returns:
            UpdateProgressResponse with the updated progress state

        Raises:
            Forbidden: If user is not enrolled and not course owner
            BadRequest: If position is invalid or both mark_complete and mark_incomplete are True
        """
        # Validate mutually exclusive flags
        if mark_complete and mark_incomplete:
            raise BadRequest(
                "markComplete and markIncomplete are mutually exclusive",
                code="mutually_exclusive_flags",
            )

        # Validate path-param UUID shape before any repo I/O so malformed input
        # returns a clean 404 instead of bubbling a psycopg InvalidTextRepresentation.
        if not _is_valid_uuid(course_id):
            raise NotFound("Course not found")
        if not _is_valid_uuid(lesson_id):
            raise NotFound("Lesson not found")

        # Check authorization
        if not self._check_authorization(user_sub, course_id):
            raise Forbidden(
                "Enrollment required to update lesson progress",
                code="enrollment_required",
            )

        # Validate position
        self._validate_position(position, duration)

        lesson = self._course_repo.get_lesson_by_id(course_id, lesson_id)
        if lesson is None:
            raise NotFound("Lesson not found")

        # Determine completion status
        completed: bool
        if mark_complete:
            completed = True
        elif mark_incomplete:
            completed = False
        else:
            # Auto-complete based on position/duration ratio
            completed = self._compute_auto_complete(position, duration)

        # Upsert progress
        row = self._progress_repo.upsert_progress(
            user_sub=user_sub,
            lesson_id=lesson_id,
            course_id=course_id,
            completed=completed,
            last_position_sec=position,
        )

        # If we have a valid duration, try to populate lesson duration (best effort)
        # Any enrolled user or owner can trigger this if the lesson has no duration yet
        if duration > 0:
            try:
                self._course_repo.set_lesson_duration(course_id, lesson_id, duration)
            except Exception:
                # Silently ignore - duration update is best-effort, shouldn't break progress tracking
                pass

        # Build response
        lesson_progress: LessonProgressItem = {
            "lessonId": row.lesson_id,
            "completed": row.completed,
            "lastPositionSec": row.last_position_sec,
        }
        if row.completed and row.completed_at:
            lesson_progress["completedAt"] = row.completed_at.isoformat()

        return {
            "ok": True,
            "lessonProgress": lesson_progress,
        }
