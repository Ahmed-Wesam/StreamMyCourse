"""RS-5 Slice C: purchase checkout precheck service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple
from unittest.mock import MagicMock

import pytest

from services.purchases.checkout_service import (
    INCOMPLETE_CHECKOUT_TTL_MINUTES,
    PurchaseCheckoutService,
)
from services.purchases.models import BundleOffer
from services.purchases.repo import PurchaseRdsRepository

COURSE_ID = "b0000000-0000-4000-8000-000000000001"
PURCHASE_ID = "c0000000-0000-4000-8000-000000000001"


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    fetchone_results: List[Optional[Tuple[Any, ...]]] = field(default_factory=list)
    rowcount: int = 0

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    autocommit: bool = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _service() -> tuple[PurchaseCheckoutService, PurchaseRdsRepository, FakeConn]:
    conn = FakeConn()
    repo = PurchaseRdsRepository(lambda: conn, deployment_environment="dev")
    return PurchaseCheckoutService(repo), repo, conn


class TestPurchaseCheckoutPrecheck:
    def test_already_owned_course_via_bundle(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [(1,)]  # bundle paid on ownership check

        result = svc.run_purchase_checkout_precheck(
            "student-sub", product_type="course", course_id=COURSE_ID
        )

        assert result == {"blockReason": "already_owned"}

    def test_course_precheck_reserves_pending(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [
            None,  # bundle
            None,  # course paid
            (50_000,),  # course price (50 JOD fils)
            None,  # fresh pending in txn
            (PURCHASE_ID,),  # INSERT RETURNING id
        ]

        result = svc.run_purchase_checkout_precheck(
            "student-sub", product_type="course", course_id=COURSE_ID
        )

        assert result["blockReason"] is None
        assert result["product"]["amount_minor"] == 50_000
        assert result["product"]["currency"] == "JOD"
        assert result["product"]["purchase_id"] == PURCHASE_ID
        assert str(INCOMPLETE_CHECKOUT_TTL_MINUTES) in str(conn.cursor_obj.executions)

    def test_bundle_precheck_uses_bundle_offer(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [
            None,  # bundle paid check
            (150_000, "JOD"),  # bundle offer (150 JOD fils)
            None,  # fresh pending
            (PURCHASE_ID,),  # INSERT RETURNING id
        ]

        result = svc.run_purchase_checkout_precheck("student-sub", product_type="bundle")

        assert result == {
            "blockReason": None,
            "product": {
                "amount_minor": 150_000,
                "currency": "JOD",
                "product_type": "bundle",
                "purchase_id": PURCHASE_ID,
            },
        }

    def test_checkout_in_progress_block(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [
            None,
            None,
            (50_000,),
            (1,),  # fresh pending
        ]

        result = svc.run_purchase_checkout_precheck(
            "student-sub", product_type="course", course_id=COURSE_ID
        )

        assert result == {"blockReason": "checkout_in_progress"}

    def test_rollback_deletes_pending(self) -> None:
        svc, _repo, conn = _service()
        svc.rollback_purchase_checkout_precheck(
            "student-sub", product_type="course", course_id=COURSE_ID
        )
        sql, _ = conn.cursor_obj.executions[0]
        assert "DELETE" in sql.upper()


class TestPurchaseInternalCheckout:
    def test_internal_handler_requires_course_id_for_course(self) -> None:
        from services.purchases.internal_checkout import handle_internal_purchase_checkout

        mock_svc = MagicMock()
        with pytest.raises(ValueError, match="courseId"):
            handle_internal_purchase_checkout(
                {"userSub": "u", "productType": "course"},
                checkout_service=mock_svc,
            )

    def test_internal_handler_dispatches(self) -> None:
        from services.purchases.internal_checkout import handle_internal_purchase_checkout

        mock_svc = MagicMock()
        mock_svc.run_purchase_checkout_precheck.return_value = {"blockReason": None, "product": {}}
        out = handle_internal_purchase_checkout(
            {
                "userSub": "u",
                "productType": "bundle",
            },
            checkout_service=mock_svc,
        )
        assert out["blockReason"] is None
        mock_svc.run_purchase_checkout_precheck.assert_called_once_with(
            "u", product_type="bundle", course_id=None
        )


class TestPurchaseStatusRead:
    def test_returns_pending_status(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [("pending",)]

        result = svc.get_purchase_status("student-sub", purchase_id=PURCHASE_ID)

        assert result == {"status": "pending"}

    def test_returns_paid_status(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [("paid",)]

        result = svc.get_purchase_status("student-sub", purchase_id=PURCHASE_ID)

        assert result == {"status": "paid"}

    def test_returns_failed_status(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [("failed",)]

        result = svc.get_purchase_status("student-sub", purchase_id=PURCHASE_ID)

        assert result == {"status": "failed"}

    def test_not_found_when_row_missing(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [None]

        result = svc.get_purchase_status("student-sub", purchase_id=PURCHASE_ID)

        assert result == {"blockReason": "not_found"}

    def test_wrong_user_cannot_read_another_users_purchase(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [None]

        result = svc.get_purchase_status(
            "other-user-sub",
            purchase_id=PURCHASE_ID,
        )

        assert result == {"blockReason": "not_found"}
        _, params = conn.cursor_obj.executions[0]
        assert params[1] == "other-user-sub"


class TestPurchaseCheckoutStatusVerify:
    def test_checkout_status_returns_purchase_status(self) -> None:
        svc, _repo, conn = _service()
        conn.cursor_obj.fetchone_results = [("pending",)]

        result = svc.get_purchase_status(
            "student-sub",
            purchase_id=PURCHASE_ID,
        )

        assert result == {"status": "pending"}

    def test_internal_checkout_status_handler(self) -> None:
        from services.purchases.internal_checkout import handle_internal_purchase_checkout_status

        mock_svc = MagicMock()
        mock_svc.get_purchase_status.return_value = {"status": "pending"}
        out = handle_internal_purchase_checkout_status(
            {
                "userSub": "u",
                "purchaseId": PURCHASE_ID,
            },
            checkout_service=mock_svc,
        )
        assert out == {"status": "pending"}
        mock_svc.get_purchase_status.assert_called_once_with(
            "u",
            purchase_id=PURCHASE_ID,
        )
