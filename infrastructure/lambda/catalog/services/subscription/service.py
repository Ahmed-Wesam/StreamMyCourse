"""has_course_access domain rules (access-policy-v1)."""

from __future__ import annotations

import logging

from services.course_management.models import Course
from services.course_management.ports import CourseCatalogRepositoryPort
from services.subscription.ports import SubscriptionRepositoryPort


logger = logging.getLogger(__name__)


class CourseAccessService:
    """Central subscription access checks; does not use enrollments for access."""

    def __init__(
        self,
        subscription_repo: SubscriptionRepositoryPort,
        course_repo: CourseCatalogRepositoryPort,
    ) -> None:
        self._subscription_repo = subscription_repo
        self._course_repo = course_repo

    def has_granting_subscription(self, user_sub: str) -> bool:
        return self._subscription_repo.has_granting_subscription(user_sub)

    def has_course_access(
        self,
        user_sub: str,
        course_id: str,
        role: str,
        *,
        course: Course | None = None,
    ) -> bool:
        normalized_sub = (user_sub or "").strip()
        if not normalized_sub:
            return False
        if course is None:
            course = self._course_repo.get_course(course_id)
        if course is None:
            return False
        if self._is_owner_or_admin(course, user_sub=normalized_sub, role=role):
            return True
        if course.status != "PUBLISHED":
            return False
        return self._subscription_repo.has_granting_subscription(normalized_sub)

    def _norm_role(self, role: str) -> str:
        return (role or "").strip().lower()

    def _is_admin(self, role: str) -> bool:
        return self._norm_role(role) == "admin"

    def _is_owner_or_admin(self, course: Course, *, user_sub: str, role: str) -> bool:
        if self._is_admin(role):
            return True
        if self._norm_role(role) != "teacher":
            return False
        owner = (course.createdBy or "").strip()
        if not owner:
            logger.warning("course %s has blank createdBy — denying owner bypass", course.id)
            return False
        return owner == user_sub
