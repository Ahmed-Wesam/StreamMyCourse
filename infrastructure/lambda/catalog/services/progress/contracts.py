from __future__ import annotations

from typing import Any, List, NotRequired, TypedDict


class CourseProgressLessonItem(TypedDict):
    lessonId: str
    completed: bool
    completedAt: str | None
    lastPositionSec: int


class CourseProgressResponse(TypedDict):
    courseId: str
    totalReadyLessons: int
    completedCount: int
    percentComplete: float
    lessons: List[CourseProgressLessonItem]


class LessonProgressUpdateResponse(TypedDict):
    ok: bool
    throttled: NotRequired[bool]
