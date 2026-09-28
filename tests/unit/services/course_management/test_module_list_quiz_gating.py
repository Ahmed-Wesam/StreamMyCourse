"""RS-8 slice 4: locked + moduleQuiz pass fields on GET /courses/{id}/modules."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.course_management.models import Course, CourseModule
from services.course_management.service import CourseManagementService

_VID = "11111111-1111-4111-8111-111111111111"
_M1 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_M2 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _course(*, status: str = "PUBLISHED") -> Course:
    return Course(
        id=_VID,
        title="T",
        description="D",
        status=status,
        createdBy="owner-sub",
    )


def _module(*, id_: str, order: int) -> CourseModule:
    return CourseModule(
        id=id_,
        courseId=_VID,
        title=f"Mod {order}",
        description="",
        order=order,
    )


def _service(
    *,
    repo: MagicMock,
    course_access: MagicMock,
    visibility: MagicMock | None = None,
    module_lock: MagicMock | None = None,
) -> CourseManagementService:
    return CourseManagementService(
        repo,
        None,
        course_access=course_access,
        module_quiz_visibility=visibility,
        module_lock=module_lock,
    )


def test_enrolled_student_modules_include_locked_and_module_quiz_pass_fields() -> None:
    repo = MagicMock()
    course_access = MagicMock()
    course_access.has_course_access.return_value = True
    visibility = MagicMock()
    module_lock = MagicMock()
    repo.get_course.return_value = _course()
    repo.list_course_modules.return_value = [
        _module(id_=_M1, order=0),
        _module(id_=_M2, order=1),
    ]
    visibility.module_quiz_visibility_by_course.return_value = {
        _M1: {
            "available": True,
            "servedCountN": 3,
            "passPercent": 80,
            "passed": True,
        },
        _M2: {
            "available": True,
            "servedCountN": 2,
            "passPercent": 70,
            "passed": False,
        },
    }
    module_lock.is_module_locked_for_student.side_effect = lambda _c, mid, **_: mid == _M2

    svc = _service(
        repo=repo,
        course_access=course_access,
        visibility=visibility,
        module_lock=module_lock,
    )
    out = svc.list_course_modules_public(
        _VID, cognito_sub="student-sub", role="student"
    )

    assert out[0]["locked"] is False
    assert out[0]["moduleQuiz"]["passPercent"] == 80
    assert out[0]["moduleQuiz"]["passed"] is True
    assert out[1]["locked"] is True
    assert out[1]["moduleQuiz"]["passed"] is False


def test_anonymous_catalog_omits_locked_and_pass_fields() -> None:
    repo = MagicMock()
    course_access = MagicMock()
    visibility = MagicMock()
    module_lock = MagicMock()
    course_access.has_course_access.return_value = False
    repo.get_course.return_value = _course()
    repo.list_course_modules.return_value = [_module(id_=_M1, order=0)]
    visibility.module_quiz_visibility_by_course.return_value = {}

    svc = _service(
        repo=repo,
        course_access=course_access,
        visibility=visibility,
        module_lock=module_lock,
    )
    out = svc.list_course_modules_public(_VID, cognito_sub="", role="")

    assert "locked" not in out[0]
    assert "moduleQuiz" not in out[0]
    module_lock.is_module_locked_for_student.assert_not_called()
