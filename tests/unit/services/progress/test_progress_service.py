"""Unit tests for `services.progress.service.LessonProgressService`.

The service is constructor-injected with repo ports, so we hand it MagicMock doubles
directly. No patching of module globals — the ports are the only seam we need.
"""

from __future__ import annotations

from typing import List, Optional
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, Forbidden
from services.progress.ports import LessonProgressRow


# Helper to create LessonProgressRow
def _progress_row(
    user_sub: str = "user-1",
    lesson_id: str = "lesson-1",
    course_id: str = "course-1",
    completed: bool = False,
    completed_at: Optional[str] = None,
    last_position_sec: int = 0,
    updated_at: str = "2026-01-01T00:00:00Z",
) -> LessonProgressRow:
    return LessonProgressRow(
        user_sub=user_sub,
        lesson_id=lesson_id,
        course_id=course_id,
        completed=completed,
        completed_at=completed_at,
        last_position_sec=last_position_sec,
        updated_at=updated_at,
    )


@pytest.fixture
def progress_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def enrollment_repo() -> MagicMock:
    m = MagicMock()
    m.has_enrollment.return_value = False
    return m


@pytest.fixture
def course_repo() -> MagicMock:
    m = MagicMock()
    return m


@pytest.fixture
def service(
    progress_repo: MagicMock,
    enrollment_repo: MagicMock,
    course_repo: MagicMock,
) -> "LessonProgressService":
    from services.progress.service import LessonProgressService

    return LessonProgressService(
        progress_repo=progress_repo,
        enrollment_repo=enrollment_repo,
        course_repo=course_repo,
        progress_complete_ratio=0.92,
        position_slack_sec=30,
    )


# --- Authorization tests ------------------------------------------------------


class TestAuthorization:
    def test_rejects_unenrolled_user(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """User not enrolled AND not course owner → Forbidden with enrollment_required code."""
        enrollment_repo.has_enrollment.return_value = False
        # Mock course with different owner
        course_repo.get_course.return_value = MagicMock(createdBy="other-teacher")

        with pytest.raises(Forbidden) as exc_info:
            service.update_lesson_progress(
                user_sub="student-1",
                course_id="course-1",
                lesson_id="lesson-1",
                position=10,
                duration=100,
            )

        assert exc_info.value.code == "enrollment_required"

    def test_allows_course_owner_without_enrollment(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Teacher can see/update progress for their own course without enrollment."""
        enrollment_repo.has_enrollment.return_value = False
        # Teacher is the course owner
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        progress_repo.upsert_progress.return_value = _progress_row(
            user_sub="teacher-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=False,
            last_position_sec=50,
        )

        result = service.update_lesson_progress(
            user_sub="teacher-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=50,
            duration=100,
        )

        assert result["ok"] is True
        assert result["lessonProgress"]["lessonId"] == "lesson-1"
        assert result["lessonProgress"]["lastPositionSec"] == 50

    def test_allows_enrolled_student(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Enrolled student can update progress."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        progress_repo.upsert_progress.return_value = _progress_row(
            user_sub="student-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=False,
            last_position_sec=25,
        )

        result = service.update_lesson_progress(
            user_sub="student-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=25,
            duration=100,
        )

        assert result["ok"] is True


# --- Auto-complete logic tests ------------------------------------------------


class TestAutoCompleteLogic:
    def test_auto_completes_at_ratio_threshold(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Position/duration >= 0.92 → completed=True."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        # 92 / 100 = 0.92, exactly at threshold
        progress_repo.upsert_progress.return_value = _progress_row(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=True,
            completed_at="2026-01-01T00:00:00Z",
            last_position_sec=92,
        )

        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=92,
            duration=100,
        )

        # Verify upsert was called with completed=True
        call_kwargs = progress_repo.upsert_progress.call_args.kwargs
        assert call_kwargs["completed"] is True
        assert result["lessonProgress"]["completed"] is True

    def test_does_not_auto_complete_below_threshold(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Position/duration < 0.92 → completed=False."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        progress_repo.upsert_progress.return_value = _progress_row(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=False,
            last_position_sec=91,
        )

        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=91,
            duration=100,
        )

        call_kwargs = progress_repo.upsert_progress.call_args.kwargs
        assert call_kwargs["completed"] is False
        assert result["lessonProgress"]["completed"] is False

    def test_auto_completes_above_threshold(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Position/duration > 0.92 → completed=True."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        progress_repo.upsert_progress.return_value = _progress_row(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=True,
            completed_at="2026-01-01T00:00:00Z",
            last_position_sec=95,
        )

        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=95,
            duration=100,
        )

        call_kwargs = progress_repo.upsert_progress.call_args.kwargs
        assert call_kwargs["completed"] is True
        assert result["lessonProgress"]["completed"] is True


# --- Position validation tests ------------------------------------------------


class TestPositionValidation:
    def test_position_slack_allows_within_threshold(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """position <= duration + 30 is allowed."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")

        # position = 130, duration = 100, slack = 30, so 130 <= 130 is allowed
        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=130,
            duration=100,
        )

        assert result["ok"] is True

    def test_position_slack_rejects_excessive(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """position > duration + 30 → BadRequest."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")

        # position = 131, duration = 100, slack = 30, so 131 > 130 is rejected
        with pytest.raises(BadRequest) as exc_info:
            service.update_lesson_progress(
                user_sub="user-1",
                course_id="course-1",
                lesson_id="lesson-1",
                position=131,
                duration=100,
            )

        assert "position" in exc_info.value.message.lower()

    def test_unknown_duration_allows_position_beyond_slack(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """duration=0 means unknown length; do not cap position at 0 + slack."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")

        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=600,
            duration=0,
        )

        assert result["ok"] is True


# --- Explicit mark complete/incomplete tests ----------------------------------


class TestExplicitMarkComplete:
    def test_mark_complete_sets_completed_true(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Explicit markComplete=True action sets completed=True regardless of position."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        progress_repo.upsert_progress.return_value = _progress_row(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=True,
            completed_at="2026-01-01T00:00:00Z",
            last_position_sec=5,
        )

        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=5,
            duration=100,
            mark_complete=True,
        )

        call_kwargs = progress_repo.upsert_progress.call_args.kwargs
        assert call_kwargs["completed"] is True
        assert result["lessonProgress"]["completed"] is True

    def test_mark_incomplete_clears_completion(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Explicit markIncomplete=True action sets completed=False."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        progress_repo.upsert_progress.return_value = _progress_row(
            user_sub="user-1",
            lesson_id="lesson-1",
            course_id="course-1",
            completed=False,
            last_position_sec=100,
        )

        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=100,
            duration=100,
            mark_incomplete=True,
        )

        call_kwargs = progress_repo.upsert_progress.call_args.kwargs
        assert call_kwargs["completed"] is False
        assert result["lessonProgress"]["completed"] is False

    def test_mutually_exclusive_mark_complete_and_incomplete(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Both markComplete=True and markIncomplete=True → BadRequest."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")

        with pytest.raises(BadRequest) as exc_info:
            service.update_lesson_progress(
                user_sub="user-1",
                course_id="course-1",
                lesson_id="lesson-1",
                position=50,
                duration=100,
                mark_complete=True,
                mark_incomplete=True,
            )

        assert "mutually exclusive" in exc_info.value.message.lower()


# --- Get course progress tests ------------------------------------------------


class TestGetCourseProgress:
    def test_get_course_progress_returns_aggregate(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Returns correct totals and percent for course progress."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        # Mock 3 lessons in the course
        course_repo.list_lessons.return_value = [
            MagicMock(id="lesson-1"),
            MagicMock(id="lesson-2"),
            MagicMock(id="lesson-3"),
        ]
        # Mock 3 progress records: 2 completed, 1 not completed
        progress_repo.get_progress_for_course.return_value = [
            _progress_row(lesson_id="lesson-1", completed=True, last_position_sec=100),
            _progress_row(lesson_id="lesson-2", completed=True, last_position_sec=90),
            _progress_row(lesson_id="lesson-3", completed=False, last_position_sec=30),
        ]

        result = service.get_course_progress(
            user_sub="user-1",
            course_id="course-1",
        )

        assert result["courseId"] == "course-1"
        assert result["totalReadyLessons"] == 3
        assert result["completedCount"] == 2
        assert result["percentComplete"] == pytest.approx(66.67, 0.01)
        assert len(result["lessons"]) == 3

    def test_get_course_progress_empty_course(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Empty course returns 0 counts and 0%."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        # No lessons in the course
        course_repo.list_lessons.return_value = []
        progress_repo.get_progress_for_course.return_value = []

        result = service.get_course_progress(
            user_sub="user-1",
            course_id="course-1",
        )

        assert result["courseId"] == "course-1"
        assert result["totalReadyLessons"] == 0
        assert result["completedCount"] == 0
        assert result["percentComplete"] == 0.0
        assert result["lessons"] == []

    def test_get_course_progress_all_completed(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """All lessons completed returns 100%."""
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        course_repo.list_lessons.return_value = [
            MagicMock(id="lesson-1"),
            MagicMock(id="lesson-2"),
        ]
        progress_repo.get_progress_for_course.return_value = [
            _progress_row(lesson_id="lesson-1", completed=True, last_position_sec=100),
            _progress_row(lesson_id="lesson-2", completed=True, last_position_sec=90),
        ]

        result = service.get_course_progress(
            user_sub="user-1",
            course_id="course-1",
        )

        assert result["completedCount"] == 2
        assert result["percentComplete"] == 100.0

    def test_get_course_progress_teacher_owner(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Teacher can get progress for their own course."""
        enrollment_repo.has_enrollment.return_value = False
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        course_repo.list_lessons.return_value = [
            MagicMock(id="lesson-1"),
        ]
        progress_repo.get_progress_for_course.return_value = [
            _progress_row(user_sub="student-1", lesson_id="lesson-1", completed=True),
        ]

        result = service.get_course_progress(
            user_sub="teacher-1",
            course_id="course-1",
        )

        assert result["courseId"] == "course-1"
        assert result["totalReadyLessons"] == 1

    def test_get_course_progress_merges_with_all_lessons(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Returns progress for all lessons, including those without progress records.

        This is the regression test for: completing 1 lesson should not mark all as complete.
        The bug was that only lessons with progress records were returned, causing
        the frontend to not find progress for other lessons.
        """
        enrollment_repo.has_enrollment.return_value = True
        course_repo.get_course.return_value = MagicMock(createdBy="teacher-1")
        # 3 lessons in course, but user only has progress for 1 (completed)
        course_repo.list_lessons.return_value = [
            MagicMock(id="lesson-1"),
            MagicMock(id="lesson-2"),
            MagicMock(id="lesson-3"),
        ]
        progress_repo.get_progress_for_course.return_value = [
            _progress_row(lesson_id="lesson-1", completed=True, last_position_sec=100),
        ]

        result = service.get_course_progress(
            user_sub="user-1",
            course_id="course-1",
        )

        # Should report all 3 lessons
        assert result["totalReadyLessons"] == 3
        assert result["completedCount"] == 1
        assert result["percentComplete"] == pytest.approx(33.33, 0.01)
        assert len(result["lessons"]) == 3

        # Verify all lessons are in result with correct completion status
        lessons_by_id = {l["lessonId"]: l for l in result["lessons"]}
        assert lessons_by_id["lesson-1"]["completed"] is True
        assert lessons_by_id["lesson-1"]["lastPositionSec"] == 100
        # Lessons without progress should have default "not started" values
        assert lessons_by_id["lesson-2"]["completed"] is False
        assert lessons_by_id["lesson-2"]["lastPositionSec"] == 0
        assert lessons_by_id["lesson-3"]["completed"] is False
        assert lessons_by_id["lesson-3"]["lastPositionSec"] == 0


class TestDurationUpdateOnProgress:
    """Tests for lesson duration population via progress updates."""

    def test_update_progress_with_duration_calls_set_lesson_duration(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """When progress update includes valid duration, lesson duration should be updated."""
        enrollment_repo.has_enrollment.return_value = True
        progress_repo.upsert_progress.return_value = _progress_row(
            lesson_id="lesson-1", completed=False, last_position_sec=30
        )

        service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=30,
            duration=120,  # Valid duration from video metadata
        )

        # Should call set_lesson_duration on course_repo
        course_repo.set_lesson_duration.assert_called_once_with("course-1", "lesson-1", 120)

    def test_update_progress_with_zero_duration_skips_set_lesson_duration(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Duration of 0 should not trigger lesson duration update."""
        enrollment_repo.has_enrollment.return_value = True
        progress_repo.upsert_progress.return_value = _progress_row(
            lesson_id="lesson-1", completed=False, last_position_sec=0
        )

        service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=0,
            duration=0,  # No duration available
        )

        # Should NOT call set_lesson_duration
        course_repo.set_lesson_duration.assert_not_called()

    def test_update_progress_duration_error_silently_ignored(
        self,
        service: "LessonProgressService",
        enrollment_repo: MagicMock,
        progress_repo: MagicMock,
        course_repo: MagicMock,
    ) -> None:
        """Errors in duration update should not break progress tracking."""
        enrollment_repo.has_enrollment.return_value = True
        progress_repo.upsert_progress.return_value = _progress_row(
            lesson_id="lesson-1", completed=False, last_position_sec=30
        )
        # Simulate error in duration update
        course_repo.set_lesson_duration.side_effect = Exception("DB error")

        # Should not raise despite the error
        result = service.update_lesson_progress(
            user_sub="user-1",
            course_id="course-1",
            lesson_id="lesson-1",
            position=30,
            duration=120,
        )

        # Progress update should still succeed
        assert result["ok"] is True
        course_repo.set_lesson_duration.assert_called_once()
