"""Ports for subscription-based course access (WS5)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from services.course_management.ports import CourseCatalogRepositoryPort

if TYPE_CHECKING:
    from services.course_management.models import Course


class SubscriptionRepositoryPort(Protocol):
    def has_granting_subscription(self, user_sub: str) -> bool: ...


class CourseAccessPort(Protocol):
    """Frozen for W5-P3+ consumers (course_management, progress, bootstrap adapter)."""

    def has_granting_subscription(self, user_sub: str) -> bool: ...

    def has_course_access(
        self,
        user_sub: str,
        course_id: str,
        role: str,
        *,
        course: "Course | None" = None,
    ) -> bool: ...


__all__ = [
    "CourseAccessPort",
    "CourseCatalogRepositoryPort",
    "SubscriptionRepositoryPort",
]
