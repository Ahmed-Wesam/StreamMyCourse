"""RS-8 slice 3: module_locked on update_lesson_progress only."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden
from services.progress.service import LessonProgressService


_COURSE_ID = "11111111-1111-1111-1111-111111111111"
_LESSON_ID = "22222222-2222-2222-2222-222222222222"
_MODULE_ID = "33333333-3333-3333-3333-333333333333"


@pytest.fixture
def progress_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def course_access() -> MagicMock:
    m = MagicMock()
    m.has_course_access.return_value = True
    return m


@pytest.fixture
def course_repo() -> MagicMock:
    return MagicMock()


@pytest.fixture
def module_lock() -> MagicMock:
    m = MagicMock()
    m.is_module_locked_for_student.return_value = False
    return m


@pytest.fixture
def service(
    progress_repo: MagicMock,
    course_access: MagicMock,
    course_repo: MagicMock,
    module_lock: MagicMock,
) -> LessonProgressService:
    return LessonProgressService(
        progress_repo=progress_repo,
        course_access=course_access,
        course_repo=course_repo,
        module_lock=module_lock,
    )


def test_update_lesson_progress_raises_module_locked(
    service: LessonProgressService,
    course_repo: MagicMock,
    module_lock: MagicMock,
    progress_repo: MagicMock,
) -> None:
    course_repo.get_lesson_by_id.return_value = MagicMock(
        id=_LESSON_ID, moduleId=_MODULE_ID
    )
    module_lock.is_module_locked_for_student.return_value = True

    with pytest.raises(Forbidden) as exc_info:
        service.update_lesson_progress(
            user_sub="student-1",
            course_id=_COURSE_ID,
            lesson_id=_LESSON_ID,
            position=10,
            duration=100,
            role="student",
        )

    assert exc_info.value.code == "module_locked"
    assert exc_info.value.status_code == 403
    progress_repo.upsert_progress.assert_not_called()
    module_lock.is_module_locked_for_student.assert_called_once_with(
        _COURSE_ID,
        _MODULE_ID,
        cognito_sub="student-1",
        role="student",
    )


def test_get_course_progress_does_not_check_module_lock(
    service: LessonProgressService,
    course_repo: MagicMock,
    module_lock: MagicMock,
    progress_repo: MagicMock,
) -> None:
    course_repo.list_lessons.return_value = []
    progress_repo.get_progress_for_course.return_value = []
    module_lock.is_module_locked_for_student.return_value = True

    result = service.get_course_progress(
        user_sub="student-1",
        course_id=_COURSE_ID,
        role="student",
    )

    assert result["courseId"] == _COURSE_ID
    module_lock.is_module_locked_for_student.assert_not_called()
