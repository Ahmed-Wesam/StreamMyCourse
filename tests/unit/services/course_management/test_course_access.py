"""W5-P3/P5: course_management subscription access (not enrollment)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden
from services.course_management.models import Course
from services.course_management.service import CourseManagementService


_VID = "11111111-1111-4111-8111-111111111111"


def _course(*, status: str = "PUBLISHED", created_by: str = "owner-sub") -> Course:
    return Course(
        id=_VID,
        title="T",
        description="D",
        status=status,
        createdBy=created_by,
    )


def _service(
    *,
    has_access: bool = False,
) -> tuple[CourseManagementService, MagicMock]:
    repo = MagicMock()
    course_access = MagicMock()
    course_access.has_course_access.return_value = has_access
    svc = CourseManagementService(repo, None, course_access=course_access)
    return svc, course_access


class TestViewerHasLessonAccessUsesSubscription:
    def test_delegates_to_course_access_port(self) -> None:
        svc, course_access = _service(has_access=True)
        course = _course()

        assert (
            svc.viewer_has_lesson_access(
                course,
                course_id=_VID,
                cognito_sub="student-sub",
                role="student",
            )
            is True
        )
        course_access.has_course_access.assert_called_once_with(
            "student-sub", _VID, "student", course=course
        )


class TestEnsureCanViewLessonsAndPlayback:
    def test_without_access_raises_subscription_required(self) -> None:
        svc, course_access = _service(has_access=False)
        svc._repo.get_course.return_value = _course()
        course_access.has_course_access.return_value = False

        with pytest.raises(Forbidden) as exc_info:
            svc.ensure_can_view_lessons_and_playback(
                _VID, cognito_sub="student-sub", role="student"
            )

        assert exc_info.value.code == "subscription_required"

    def test_with_access_returns_course(self) -> None:
        svc, course_access = _service(has_access=True)
        published = _course()
        svc._repo.get_course.return_value = published
        course_access.has_course_access.return_value = True

        result = svc.ensure_can_view_lessons_and_playback(
            _VID, cognito_sub="student-sub", role="student"
        )

        assert result.id == _VID


class TestEnrollBlocked:
    def test_enroll_raises_subscription_required_without_put(self) -> None:
        svc, _ = _service()
        svc._repo.get_course.return_value = _course(status="PUBLISHED")

        with pytest.raises(Forbidden) as exc_info:
            svc.enroll_in_published_course(_VID, cognito_sub="student-sub")

        assert exc_info.value.code == "subscription_required"

    def test_enroll_with_profile_does_not_provision_user(self) -> None:
        svc, _ = _service()
        svc._repo.get_course.return_value = _course(status="PUBLISHED")
        profile = MagicMock()

        with pytest.raises(Forbidden):
            svc.enroll_in_published_course_with_profile(
                _VID,
                cognito_sub="student-sub",
                email="s@example.com",
                role="student",
                profile_provisioner=profile,
            )

        profile.get_or_create_profile.assert_not_called()


class TestCourseDetailHasAccess:
    def test_published_sets_has_access_and_enrolled_alias(self) -> None:
        svc, course_access = _service(has_access=True)
        svc._repo.get_course.return_value = _course(status="PUBLISHED")
        svc._repo.list_lessons.return_value = []
        course_access.has_course_access.return_value = True

        out = svc.get_course_detail_with_enrollment(
            _VID, cognito_sub="student-sub", role="student"
        )

        assert out["hasAccess"] is True
        assert out["enrolled"] is True
    def test_anonymous_published_has_access_false(self) -> None:
        svc, course_access = _service(has_access=False)
        svc._repo.get_course.return_value = _course(status="PUBLISHED")
        svc._repo.list_lessons.return_value = []
        course_access.has_course_access.return_value = False

        out = svc.get_course_detail_with_enrollment(_VID, cognito_sub="", role="")

        assert out["hasAccess"] is False
        assert out["enrolled"] is False


class TestListLessonsPublicUnchanged:
    def test_published_list_does_not_call_course_access(self) -> None:
        svc, course_access = _service()
        svc._repo.get_course.return_value = _course(status="PUBLISHED")
        svc._repo.list_lessons.return_value = []

        rows = svc.list_lessons_public(_VID, cognito_sub="", role="")

        assert rows == []
        course_access.has_course_access.assert_not_called()
