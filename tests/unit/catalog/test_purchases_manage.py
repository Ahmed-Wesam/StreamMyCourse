"""RS-5 Slice C: purchase manage service (prices + list)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from services.common.errors import Forbidden, NotFound
from services.course_management.models import Course
from services.purchases.manage_service import PurchaseManageService
from services.purchases.models import BundleOffer, PurchaseRecord

COURSE_ID = "b0000000-0000-4000-8000-000000000001"


def _manage(
    *,
    billing_teacher_sub: str = "billing-teacher",
) -> tuple[PurchaseManageService, MagicMock, MagicMock]:
    purchase_repo = MagicMock()
    course_repo = MagicMock()
    svc = PurchaseManageService(
        purchase_repo,
        course_repo,
        billing_teacher_sub=billing_teacher_sub,
    )
    return svc, purchase_repo, course_repo


class TestPurchaseManageService:
    def test_set_bundle_price_billing_teacher_only(self) -> None:
        svc, purchase_repo, _ = _manage()
        purchase_repo.get_bundle_offer.return_value = BundleOffer(12000, "USD")

        offer = svc.set_bundle_price(caller_sub="billing-teacher", amount_minor=12000)

        assert offer.amount_minor == 12000
        purchase_repo.set_bundle_price.assert_called_once_with(12000)

    def test_set_bundle_price_forbidden_for_other_teacher(self) -> None:
        svc, purchase_repo, _ = _manage()
        with pytest.raises(Forbidden):
            svc.set_bundle_price(caller_sub="other-teacher", amount_minor=12000)
        purchase_repo.set_bundle_price.assert_not_called()

    def test_set_course_price_owner_teacher(self) -> None:
        svc, purchase_repo, course_repo = _manage()
        course_repo.get_course.return_value = Course(
            id=COURSE_ID,
            title="T",
            description="D",
            status="PUBLISHED",
            createdBy="teacher-sub",
        )
        purchase_repo.set_course_price.return_value = True

        payload = svc.set_course_price(
            course_id=COURSE_ID,
            caller_sub="teacher-sub",
            role="teacher",
            amount_minor=4900,
        )

        assert payload["amountMinor"] == 4900
        purchase_repo.set_course_price.assert_called_once_with(COURSE_ID, 4900)

    def test_set_course_price_forbidden_non_owner(self) -> None:
        svc, _, course_repo = _manage()
        course_repo.get_course.return_value = Course(
            id=COURSE_ID,
            title="T",
            description="D",
            status="PUBLISHED",
            createdBy="owner-sub",
        )
        with pytest.raises(Forbidden):
            svc.set_course_price(
                course_id=COURSE_ID,
                caller_sub="other-sub",
                role="teacher",
                amount_minor=4900,
            )

    def test_list_purchases_delegates_to_repo(self) -> None:
        svc, purchase_repo, _ = _manage()
        created = datetime(2026, 3, 1, tzinfo=timezone.utc)
        purchase_repo.list_purchases_for_user.return_value = [
            PurchaseRecord(
                id="p1",
                product_type="bundle",
                course_id=None,
                status="paid",
                amount_minor=15000,
                currency="USD",
                created_at=created,
            )
        ]

        rows = svc.list_purchases_for_user("student-sub")

        assert len(rows) == 1
        purchase_repo.list_purchases_for_user.assert_called_once_with("student-sub")

    def test_get_public_bundle_missing_raises_not_found(self) -> None:
        svc, purchase_repo, _ = _manage()
        purchase_repo.get_bundle_offer.return_value = None
        with pytest.raises(NotFound):
            svc.get_public_bundle_offer()
