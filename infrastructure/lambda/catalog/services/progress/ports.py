from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Protocol


@dataclass(frozen=True)
class LessonProgressRow:
    """Persistence DTO for lesson progress (row from lesson_progress table)."""

    user_sub: str
    lesson_id: str
    course_id: str
    completed: bool
    completed_at: Optional[datetime]
    last_position_sec: int
    updated_at: datetime


class LessonProgressRepositoryPort(Protocol):
    """Repository interface for lesson progress persistence."""

    def get_progress_for_course(
        self, *, user_sub: str, course_id: str
    ) -> List[LessonProgressRow]:
        """Fetch all lesson progress records for a user in a specific course."""
        ...

    def get_progress_for_lesson(
        self, *, user_sub: str, lesson_id: str
    ) -> Optional[LessonProgressRow]:
        """Fetch progress for a specific user and lesson."""
        ...

    def upsert_progress(
        self,
        *,
        user_sub: str,
        lesson_id: str,
        course_id: str,
        completed: bool,
        last_position_sec: int,
    ) -> LessonProgressRow:
        """Create or update progress for a lesson.

        If the record exists, update completed (if transitioning to True,
        also set completed_at), last_position_sec, and updated_at.
        If not exists, insert a new row.

        Returns the resulting row (including generated timestamps).
        """
        ...

    def record_activity_day(self, *, user_sub: str, day: date) -> None:
        """Insert today's UTC activity day. Existing rows stay (ON CONFLICT DO NOTHING)."""
        ...

    def list_activity_days(self, *, user_sub: str) -> list[date]:
        """UTC days this learner has recorded."""
        ...

    def list_lesson_completions(self, *, user_sub: str) -> list[ActivityEvent]: ...

    def list_quiz_attempts(self, *, user_sub: str) -> list[ActivityEvent]: ...

    def list_assignment_submissions(self, *, user_sub: str) -> list[ActivityEvent]: ...

    def list_certificates(self, *, user_sub: str) -> list[ActivityEvent]: ...


@dataclass(frozen=True)
class ActivityEvent:
    """One learner activity row. ``kind`` is a feed source, not free text."""

    kind: str
    occurred_at: datetime
    title: str
    course_id: str
    resource_id: str
    user_sub: str
