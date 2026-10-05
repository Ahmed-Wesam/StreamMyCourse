"""Ports for purchase-based course access (RS-5)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from services.course_management.ports import CourseCatalogRepositoryPort

if TYPE_CHECKING:
    from services.course_management.models import Course
    from services.purchases.models import BundleOffer, PurchaseRecord


class PurchaseRepositoryPort(Protocol):
    def has_paid_course_purchase(self, user_sub: str, course_id: str) -> bool: ...

    def has_paid_bundle(self, user_sub: str) -> bool: ...

    def get_bundle_offer(self) -> "BundleOffer | None": ...

    def set_bundle_price(self, amount_minor: int) -> None: ...

    def set_course_price(self, course_id: str, amount_minor: int) -> bool: ...

    def get_course_price_for_checkout(self, course_id: str) -> "dict[str, object] | None": ...

    def list_purchases_for_user(self, user_sub: str) -> "list[PurchaseRecord]": ...

    def has_checkout_blocking_ownership(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
    ) -> bool: ...

    def delete_stale_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
        ttl_minutes: int,
    ) -> None: ...

    def has_fresh_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
        ttl_minutes: int,
    ) -> bool: ...

    def delete_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
    ) -> None: ...

    def reserve_pending_checkout(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None,
        amount_minor: int,
        currency: str,
        ttl_minutes: int,
        provider: str = "hyperpay",
    ) -> str: ...


class CourseAccessPort(Protocol):
    """Purchase-based access for RS-5+ consumers (bootstrap adapter, course_management)."""

    def has_course_access(
        self,
        user_sub: str,
        course_id: str,
        role: str,
        *,
        course: "Course | None" = None,
    ) -> bool: ...

    def bypasses_module_lock(
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
    "PurchaseRepositoryPort",
]
