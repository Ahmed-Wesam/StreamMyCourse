"""Unit tests for lesson progress domain rules."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from services.common.errors import BadRequest, Forbidden, ServiceUnavailable
from services.course_management.models import Course, Lesson
from services.progress.ports import LessonProgressRow
from services.progress.service import LessonProgressService


class _FakeCourseRepo:
    def __init__(self, course: Course, lessons: List[Lesson]) -> None:
        self._course = course
        self._lessons = lessons

    def get_course(self, course_id: str) -> Optional[Course]:
        return self._course if self._course.id == course_id else None

    def get_lesson_by_id(self, course_id: str, lesson_id: str) -> Optional[Lesson]:
        for l in self._lessons:
            if l.id == lesson_id:
                return l
        return None

    def list_lessons(self, course_id: str) -> List[Lesson]:
        return list(self._lessons)


class _FakeEnrollments:
    def __init__(self, enrolled: bool) -> None:
        self._enrolled = enrolled

    def has_enrollment(self, *, user_sub: str, course_id: str) -> bool:
        return self._enrolled


class _FakeProgressRepo:
    def __init__(self, rows: Optional[List[LessonProgressRow]] = None) -> None:
        self.rows = list(rows or [])
        self.upserts: List[Dict[str, Any]] = []

    def list_for_course(self, *, user_sub: str, course_id: str) -> List[LessonProgressRow]:
        return [r for r in self.rows if r.user_sub == user_sub and r.course_id == course_id]

    def upsert(
        self,
        *,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        last_position_sec: int,
        completed: bool,
        completed_at_iso: Optional[str],
    ) -> None:
        self.upserts.append(
            {
                "user_sub": user_sub,
                "course_id": course_id,
                "lesson_id": lesson_id,
                "last_position_sec": last_position_sec,
                "completed": completed,
                "completed_at_iso": completed_at_iso,
            }
        )
        self.rows = [r for r in self.rows if not (r.user_sub == user_sub and r.lesson_id == lesson_id)]
        self.rows.append(
            LessonProgressRow(
                lesson_id=lesson_id,
                course_id=course_id,
                user_sub=user_sub,
                completed=completed,
                completed_at_iso=completed_at_iso,
                last_position_sec=last_position_sec,
            )
        )


def _svc(
    *,
    lessons: List[Lesson],
    enrolled: bool = True,
    progress_rows: Optional[List[LessonProgressRow]] = None,
    ratio: float = 0.92,
) -> LessonProgressService:
    course = Course(id="c1", title="t", description="", status="PUBLISHED")
    return LessonProgressService(
        _FakeCourseRepo(course, lessons),
        _FakeEnrollments(enrolled),
        _FakeProgressRepo(progress_rows),
        complete_ratio=ratio,
        position_slack_sec=10,
        min_put_interval_sec=0,
    )


def test_get_progress_auth_off_returns_503() -> None:
    svc = _svc(lessons=[Lesson(id="l1", title="L", order=1, videoStatus="ready")])
    with pytest.raises(ServiceUnavailable, match="Cognito"):
        svc.get_course_progress("c1", cognito_sub="u1", role="student", auth_enforced=False)


def test_get_progress_not_enrolled_403() -> None:
    svc = _svc(lessons=[Lesson(id="l1", title="L", order=1, videoStatus="ready")], enrolled=False)
    with pytest.raises(Forbidden):
        svc.get_course_progress("c1", cognito_sub="u1", role="student", auth_enforced=True)


def test_ratio_sets_completed() -> None:
    lesson = Lesson(id="l1", title="L", order=1, videoStatus="ready", duration=100)
    svc = _svc(lessons=[lesson])
    svc.update_lesson_progress(
        "c1",
        "l1",
        cognito_sub="u1",
        role="student",
        auth_enforced=True,
        last_position_sec=93,
        mark_complete=False,
        mark_incomplete=False,
        now_ts=1.0,
    )
    assert svc._progress.upserts[-1]["completed"] is True  # type: ignore[attr-defined]


def test_mark_incomplete_clears() -> None:
    lesson = Lesson(id="l1", title="L", order=1, videoStatus="ready", duration=100)
    row = LessonProgressRow(
        lesson_id="l1",
        course_id="c1",
        user_sub="u1",
        completed=True,
        completed_at_iso="2020-01-01T00:00:00Z",
        last_position_sec=100,
    )
    svc = _svc(lessons=[lesson], progress_rows=[row])
    svc.update_lesson_progress(
        "c1",
        "l1",
        cognito_sub="u1",
        role="student",
        auth_enforced=True,
        last_position_sec=None,
        mark_complete=False,
        mark_incomplete=True,
        now_ts=1.0,
    )
    assert svc._progress.upserts[-1]["completed"] is False  # type: ignore[attr-defined]
    assert svc._progress.upserts[-1]["completed_at_iso"] is None  # type: ignore[attr-defined]


def test_dual_marks_rejected() -> None:
    lesson = Lesson(id="l1", title="L", order=1, videoStatus="ready")
    svc = _svc(lessons=[lesson])
    with pytest.raises(BadRequest):
        svc.update_lesson_progress(
            "c1",
            "l1",
            cognito_sub="u1",
            role="student",
            auth_enforced=True,
            last_position_sec=None,
            mark_complete=True,
            mark_incomplete=True,
            now_ts=1.0,
        )
