"""RS-5 Slice A: purchase-based CourseAccessService has_course_access policy."""

from __future__ import annotations

from unittest.mock import MagicMock

from services.course_management.models import Course
from services.purchases.service import CourseAccessService


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
    paid_course: bool = False,
    paid_bundle: bool = False,
    course: Course | None = None,
    purchase_repo: MagicMock | None = None,
) -> tuple[CourseAccessService, MagicMock, MagicMock]:
    if purchase_repo is None:
        purchase_repo = MagicMock()
        purchase_repo.has_paid_course_purchase.return_value = paid_course
        purchase_repo.has_paid_bundle.return_value = paid_bundle
    course_repo = MagicMock()
    course_repo.get_course.return_value = course if course is not None else _course()
    svc = CourseAccessService(purchase_repo, course_repo)
    return svc, purchase_repo, course_repo


class TestPurchaseCourseAccessService:
    def test_blank_user_sub_denied(self) -> None:
        svc, purchase_repo, _ = _service(paid_course=True, paid_bundle=True)

        assert svc.has_course_access("", "course-1", "student") is False
        assert svc.has_course_access("   ", "course-1", "student") is False
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()

    def test_missing_course_denied(self) -> None:
        svc, purchase_repo, course_repo = _service(paid_course=True, paid_bundle=True)
        course_repo.get_course.return_value = None

        assert svc.has_course_access("student-sub", "missing", "student") is False
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()

    def test_owner_teacher_bypass_without_purchase(self) -> None:
        course = _course(status="DRAFT", created_by="teacher-sub")
        svc, purchase_repo, _ = _service(paid_course=False, paid_bundle=False, course=course)

        assert svc.has_course_access("teacher-sub", "course-1", "teacher") is True
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()

    def test_admin_bypass_without_purchase(self) -> None:
        course = _course(status="DRAFT")
        svc, purchase_repo, _ = _service(paid_course=False, paid_bundle=False, course=course)

        assert svc.has_course_access("any-sub", "course-1", "admin") is True
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()

    def test_published_course_allows_signed_in_student_without_purchase(self) -> None:
        purchase_repo = MagicMock()
        svc, _, course_repo = _service(purchase_repo=purchase_repo, course=_course(status="PUBLISHED"))

        assert svc.has_course_access("student-sub", "course-1", "student") is True
        course_repo.get_course.return_value = _course(course_id="course-2", status="PUBLISHED")
        assert svc.has_course_access("student-sub", "course-2", "student") is True
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()

    def test_draft_stays_closed_until_publish(self) -> None:
        purchase_repo = MagicMock()
        course_repo = MagicMock()
        future_id = "future-course"
        course_repo.get_course.side_effect = [
            _course(course_id=future_id, status="DRAFT"),
            _course(course_id=future_id, status="PUBLISHED"),
        ]
        svc = CourseAccessService(purchase_repo, course_repo)

        assert svc.has_course_access("student-sub", future_id, "student") is False
        assert svc.has_course_access("student-sub", future_id, "student") is True
        purchase_repo.has_paid_bundle.assert_not_called()
        purchase_repo.has_paid_course_purchase.assert_not_called()

    def test_unpublished_course_denied_even_with_paid_course_row(self) -> None:
        svc, purchase_repo, _ = _service(
            paid_course=True,
            paid_bundle=False,
            course=_course(status="DRAFT", created_by="other-teacher"),
        )

        assert svc.has_course_access("student-sub", "course-1", "student") is False
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()

    def test_unpublish_denies_student(self) -> None:
        purchase_repo = MagicMock()
        course_repo = MagicMock()
        course_repo.get_course.return_value = _course(status="PUBLISHED")
        svc = CourseAccessService(purchase_repo, course_repo)

        assert svc.has_course_access("student-sub", "course-1", "student") is True

        course_repo.get_course.return_value = _course(status="DRAFT", created_by="other-teacher")
        assert svc.has_course_access("student-sub", "course-1", "student") is False
        purchase_repo.has_paid_course_purchase.assert_not_called()

    def test_no_purchase_still_allows_published_course(self) -> None:
        enrollment_repo = MagicMock()
        svc, purchase_repo, course_repo = _service(
            paid_course=False,
            paid_bundle=False,
            course=_course(status="PUBLISHED"),
        )
        setattr(svc, "_enrollment_repo", enrollment_repo)

        assert svc.has_course_access("student-sub", "course-1", "student") is True
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()
        enrollment_repo.has_enrollment.assert_not_called()
        course_repo.get_course.assert_called_once_with("course-1")

    def test_draft_without_owner_or_admin_denied_without_purchase_checks(self) -> None:
        svc, purchase_repo, _ = _service(
            paid_course=True,
            paid_bundle=True,
            course=_course(status="DRAFT", created_by="other-teacher"),
        )

        assert svc.has_course_access("student-sub", "course-1", "student") is False
        purchase_repo.has_paid_course_purchase.assert_not_called()
        purchase_repo.has_paid_bundle.assert_not_called()

    def test_passed_course_skips_repo_get_course(self) -> None:
        course = _course(status="PUBLISHED")
        svc, purchase_repo, course_repo = _service(paid_course=True, paid_bundle=False, course=course)

        assert svc.has_course_access("student-sub", "course-1", "student", course=course) is True
        course_repo.get_course.assert_not_called()
        purchase_repo.has_paid_course_purchase.assert_not_called()
