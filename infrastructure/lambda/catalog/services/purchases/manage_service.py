"""HTTP-facing purchase and price management (RS-5)."""

from __future__ import annotations

from typing import Any

from services.common.errors import BadRequest, Forbidden, NotFound
from services.course_management.ports import CourseCatalogRepositoryPort
from services.purchases.models import BundleOffer, PurchaseRecord
from services.purchases.repo import PurchaseRdsRepository


class PurchaseManageService:
    def __init__(
        self,
        purchase_repo: PurchaseRdsRepository,
        course_repo: CourseCatalogRepositoryPort,
        *,
        billing_teacher_sub: str,
    ) -> None:
        self._purchase_repo = purchase_repo
        self._course_repo = course_repo
        self._billing_teacher_sub = (billing_teacher_sub or "").strip()

    def get_public_bundle_offer(self) -> BundleOffer:
        offer = self._purchase_repo.get_bundle_offer()
        if offer is None:
            raise NotFound("Bundle offer is not configured", code="bundle_not_configured")
        return offer

    def list_purchases_for_user(self, user_sub: str) -> list[PurchaseRecord]:
        return self._purchase_repo.list_purchases_for_user(user_sub)

    def set_bundle_price(self, *, caller_sub: str, amount_minor: int) -> BundleOffer:
        if not self._billing_teacher_sub:
            raise NotFound("Billing is not configured", code="billing_unconfigured")
        if caller_sub != self._billing_teacher_sub:
            raise Forbidden("Forbidden")
        if amount_minor <= 0:
            raise BadRequest("amountMinor must be a positive integer", code="invalid_amount")
        self._purchase_repo.set_bundle_price(amount_minor)
        offer = self._purchase_repo.get_bundle_offer()
        if offer is None:
            raise NotFound("Bundle offer is not configured", code="bundle_not_configured")
        return offer

    def set_course_price(
        self,
        *,
        course_id: str,
        caller_sub: str,
        role: str,
        amount_minor: int,
    ) -> dict[str, Any]:
        if amount_minor <= 0:
            raise BadRequest("amountMinor must be a positive integer", code="invalid_amount")
        course = self._course_repo.get_course(course_id)
        if course is None:
            raise NotFound("Course not found", code="course_not_found")
        normalized_role = (role or "").strip().lower()
        if normalized_role == "admin":
            pass
        elif normalized_role == "teacher" and (course.createdBy or "").strip() == caller_sub:
            pass
        else:
            raise Forbidden("Forbidden")
        updated = self._purchase_repo.set_course_price(course_id, amount_minor)
        if not updated:
            raise NotFound("Course not found", code="course_not_found")
        return {"courseId": course_id, "amountMinor": amount_minor, "currency": "USD"}
