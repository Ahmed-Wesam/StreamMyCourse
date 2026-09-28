"""Unit tests for bootstrap ``_StudentModuleLockAdapter`` (RS-8 slice 3)."""

from __future__ import annotations

from unittest.mock import MagicMock

import bootstrap as bootstrap_mod
from services.course_management.models import Course, CourseModule


def test_adapter_bypasses_lock_for_course_owner() -> None:
    course_repo = MagicMock()
    course_repo.get_course.return_value = Course(
        id="c1",
        title="T",
        description="D",
        status="PUBLISHED",
        createdBy="teacher-sub",
    )
    course_repo.list_course_modules.return_value = [
        CourseModule(id="m1", courseId="c1", title="A", description="", order=0),
        CourseModule(id="m2", courseId="c1", title="B", description="", order=1),
    ]
    qb_repo = MagicMock()
    course_access = MagicMock()
    course_access.bypasses_module_lock.return_value = True
    adapter = bootstrap_mod._StudentModuleLockAdapter(
        course_repo, qb_repo, course_access
    )

    assert (
        adapter.is_module_locked_for_student(
            "c1", "m2", cognito_sub="teacher-sub", role="teacher"
        )
        is False
    )
    qb_repo.list_module_quiz_visibility_for_course.assert_not_called()
    course_access.bypasses_module_lock.assert_called_once()


def test_adapter_uses_gating_when_not_bypassed() -> None:
    course_repo = MagicMock()
    course_repo.get_course.return_value = Course(
        id="c1",
        title="T",
        description="D",
        status="PUBLISHED",
        createdBy="owner",
    )
    course_repo.list_course_modules.return_value = [
        CourseModule(id="m1", courseId="c1", title="A", description="", order=0),
        CourseModule(id="m2", courseId="c1", title="B", description="", order=1),
    ]
    qb_repo = MagicMock()
    qb_repo.list_module_quiz_visibility_for_course.return_value = {"m1": {"servedCountN": 2}}
    qb_repo.list_module_quiz_pass_percent_for_course.return_value = {"m1": 70}
    qb_repo.list_submitted_attempt_scores_by_module.return_value = {}
    course_access = MagicMock()
    course_access.bypasses_module_lock.return_value = False
    adapter = bootstrap_mod._StudentModuleLockAdapter(
        course_repo, qb_repo, course_access
    )

    assert (
        adapter.is_module_locked_for_student(
            "c1", "m2", cognito_sub="student-sub", role="student"
        )
        is True
    )
