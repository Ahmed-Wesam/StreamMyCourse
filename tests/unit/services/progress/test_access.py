"""W5-P4: progress authorization via CourseAccessPort + role from controller."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden
from services.progress.service import LessonProgressService


_COURSE_ID = "11111111-1111-1111-1111-111111111111"
_LESSON_ID = "22222222-2222-2222-2222-222222222222"


def _service(*, has_access: bool = False) -> tuple[LessonProgressService, MagicMock]:
    progress_repo = MagicMock()
    course_repo = MagicMock()
    course_access = MagicMock()
    course_access.has_course_access.return_value = has_access
    svc = LessonProgressService(
        progress_repo=progress_repo,
        course_access=course_access,
        course_repo=course_repo,
    )
    return svc, course_access


class TestProgressSubscriptionAccess:
    def test_get_course_progress_without_access_raises_subscription_required(self) -> None:
        svc, course_access = _service(has_access=False)
        course_access.has_course_access.return_value = False

        with pytest.raises(Forbidden) as exc_info:
            svc.get_course_progress(
                "student-sub",
                _COURSE_ID,
                role="student",
            )

        assert exc_info.value.code == "subscription_required"
        course_access.has_course_access.assert_called_once_with(
            "student-sub", _COURSE_ID, "student"
        )

    def test_get_course_progress_admin_passes_role(self) -> None:
        svc, course_access = _service(has_access=True)
        course_repo = svc._course_repo
        course_repo.list_lessons.return_value = []
        course_access.has_course_access.return_value = True

        svc.get_course_progress("admin-sub", _COURSE_ID, role="admin")

        course_access.has_course_access.assert_called_once_with(
            "admin-sub", _COURSE_ID, "admin"
        )

    def test_update_lesson_progress_without_access_raises_subscription_required(self) -> None:
        svc, course_access = _service(has_access=False)
        course_access.has_course_access.return_value = False

        with pytest.raises(Forbidden) as exc_info:
            svc.update_lesson_progress(
                user_sub="student-sub",
                course_id=_COURSE_ID,
                lesson_id=_LESSON_ID,
                position=10,
                duration=100,
                role="student",
            )

        assert exc_info.value.code == "subscription_required"

    def test_update_lesson_progress_with_access_succeeds(self) -> None:
        svc, course_access = _service(has_access=True)
        course_access.has_course_access.return_value = True
        course_repo = svc._course_repo
        course_repo.get_lesson_by_id.return_value = MagicMock(
            id=_LESSON_ID, course_id=_COURSE_ID
        )
        from datetime import datetime, timezone

        from services.progress.ports import LessonProgressRow

        svc._progress_repo.upsert_progress.return_value = LessonProgressRow(
            user_sub="student-sub",
            lesson_id=_LESSON_ID,
            course_id=_COURSE_ID,
            completed=False,
            completed_at=None,
            last_position_sec=10,
            updated_at=datetime.now(timezone.utc),
        )

        result = svc.update_lesson_progress(
            user_sub="student-sub",
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            position=10,
            duration=100,
            role="student",
        )

        assert result["ok"] is True
