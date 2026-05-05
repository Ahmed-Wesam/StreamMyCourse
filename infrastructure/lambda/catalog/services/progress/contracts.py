from __future__ import annotations

from typing import List, NotRequired, TypedDict


class LessonProgressItem(TypedDict):
    """Progress state for a single lesson."""

    lessonId: str
    completed: bool
    completedAt: NotRequired[str]
    lastPositionSec: int


class CourseProgressResponse(TypedDict):
    """Aggregated progress for a course."""

    courseId: str
    totalReadyLessons: int
    completedCount: int
    percentComplete: float
    lessons: List[LessonProgressItem]


class UpdateProgressResponse(TypedDict):
    """Result of updating lesson progress."""

    ok: bool
    lessonProgress: LessonProgressItem
