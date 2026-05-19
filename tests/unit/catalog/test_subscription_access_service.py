"""W5-P2: CourseAccessService has_course_access policy."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.course_management.models import Course
from services.subscription.service import CourseAccessService


def _course(
    *,
    course_id: str = "course-1",
    status: str = "PUBLISHED",
    created_by: str = "teacher-sub",
) -> Course:
    return Course(
        id=course_id,
        title="T",
        description="D",
        status=status,
        createdBy=created_by,
    )


def _service(
    *,
    granting: bool = False,
    course: Course | None = None,
) -> tuple[CourseAccessService, MagicMock, MagicMock]:
    subscription_repo = MagicMock()
    subscription_repo.has_granting_subscription.return_value = granting
    course_repo = MagicMock()
    course_repo.get_course.return_value = course if course is not None else _course()
    svc = CourseAccessService(subscription_repo, course_repo)
    return svc, subscription_repo, course_repo


class TestCourseAccessService:
    def test_owner_teacher_bypass_without_subscription(self) -> None:
        course = _course(status="DRAFT", created_by="teacher-sub")
        svc, sub_repo, _ = _service(granting=False, course=course)

        assert svc.has_course_access("teacher-sub", "course-1", "teacher") is True
        sub_repo.has_granting_subscription.assert_not_called()

    def test_admin_bypass_without_subscription(self) -> None:
        course = _course(status="DRAFT")
        svc, sub_repo, _ = _service(granting=False, course=course)

        assert svc.has_course_access("any-sub", "course-1", "admin") is True
        sub_repo.has_granting_subscription.assert_not_called()

    def test_published_with_granting_subscription_has_access(self) -> None:
        svc, sub_repo, _ = _service(granting=True, course=_course(status="PUBLISHED"))

        assert svc.has_course_access("student-sub", "course-1", "student") is True
        sub_repo.has_granting_subscription.assert_called_once_with("student-sub")

    def test_draft_without_owner_or_admin_denied(self) -> None:
        svc, sub_repo, _ = _service(
            granting=True,
            course=_course(status="DRAFT", created_by="other-teacher"),
        )

        assert svc.has_course_access("student-sub", "course-1", "student") is False
        sub_repo.has_granting_subscription.assert_not_called()

    def test_no_subscription_no_enrollment_denied(self) -> None:
        enrollment_repo = MagicMock()
        svc, sub_repo, course_repo = _service(granting=False, course=_course(status="PUBLISHED"))
        # Guard: service must not touch enrollment even if present on a stray attribute.
        setattr(svc, "_enrollment_repo", enrollment_repo)

        assert svc.has_course_access("student-sub", "course-1", "student") is False
        sub_repo.has_granting_subscription.assert_called_once_with("student-sub")
        enrollment_repo.has_enrollment.assert_not_called()
        course_repo.get_course.assert_called_once_with("course-1")

    def test_missing_course_denied(self) -> None:
        svc, sub_repo, course_repo = _service(granting=True)
        course_repo.get_course.return_value = None

        assert svc.has_course_access("student-sub", "missing", "student") is False
        sub_repo.has_granting_subscription.assert_not_called()

    def test_has_granting_subscription_delegates_to_repo(self) -> None:
        svc, sub_repo, _ = _service(granting=True)
        sub_repo.has_granting_subscription.return_value = True

        assert svc.has_granting_subscription("student-sub") is True
        sub_repo.has_granting_subscription.assert_called_once_with("student-sub")

    def test_passed_course_skips_repo_get_course(self) -> None:
        course = _course(status="PUBLISHED")
        svc, sub_repo, course_repo = _service(granting=True, course=course)

        assert svc.has_course_access("student-sub", "course-1", "student", course=course) is True
        course_repo.get_course.assert_not_called()
        sub_repo.has_granting_subscription.assert_called_once_with("student-sub")
