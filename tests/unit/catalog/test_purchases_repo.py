"""RS-5 Slice C: PurchaseRdsRepository SQL and behavior (fake cursor)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.purchases.repo import PurchaseRdsRepository

COURSE_ID = "b0000000-0000-4000-8000-000000000001"


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    fetchone_results: List[Optional[Tuple[Any, ...]]] = field(default_factory=list)
    fetchall_results: List[List[Tuple[Any, ...]]] = field(default_factory=list)
    rowcount: int = 0

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return None

    def fetchall(self) -> List[Tuple[Any, ...]]:
        if self.fetchall_results:
            return self.fetchall_results.pop(0)
        return []


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


def _repo(*, environment: str = "dev") -> tuple[PurchaseRdsRepository, FakeConn]:
    conn = FakeConn()
    return PurchaseRdsRepository(lambda: conn, deployment_environment=environment), conn


class TestPurchasePaidAccessSql:
    def test_has_paid_course_sql(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.fetchone_results = [(1,)]

        assert repo.has_paid_course_purchase("student-sub", COURSE_ID) is True

        sql, params = conn.cursor_obj.executions[0]
        assert "purchases" in sql
        assert "status = 'paid'" in sql
        assert "product_type = 'course'" in sql
        assert params == ("student-sub", "dev", COURSE_ID)

    def test_has_paid_bundle_sql(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.fetchone_results = [(1,)]

        assert repo.has_paid_bundle("student-sub") is True

        sql, params = conn.cursor_obj.executions[0]
        assert "product_type = 'bundle'" in sql
        assert params == ("student-sub", "dev")

    def test_blank_user_sub_skips_query(self) -> None:
        repo, conn = _repo()
        assert repo.has_paid_course_purchase("", COURSE_ID) is False
        assert repo.has_paid_bundle("  ") is False
        assert not conn.cursor_obj.executions


class TestPurchasePricingSql:
    def test_get_bundle_offer(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.fetchone_results = [(15000, "USD")]

        offer = repo.get_bundle_offer()

        assert offer is not None
        assert offer.amount_minor == 15000
        assert offer.currency == "USD"
        sql, params = conn.cursor_obj.executions[0]
        assert "bundle_offers" in sql
        assert params == ("dev",)

    def test_set_course_price(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.rowcount = 1

        assert repo.set_course_price(COURSE_ID, 9900) is True

        sql, params = conn.cursor_obj.executions[0]
        assert "price_amount_minor" in sql
        assert params == (9900, COURSE_ID)


class TestPurchaseListSql:
    def test_list_purchases_includes_paid_and_pending(self) -> None:
        repo, conn = _repo()
        created = datetime(2026, 1, 2, tzinfo=timezone.utc)
        conn.cursor_obj.fetchall_results = [
            [
                (
                    "p1",
                    "course",
                    COURSE_ID,
                    "paid",
                    9900,
                    "USD",
                    created,
                )
            ]
        ]

        records = repo.list_purchases_for_user("student-sub")

        assert len(records) == 1
        assert records[0].product_type == "course"
        sql, params = conn.cursor_obj.executions[0]
        assert "status IN ('paid', 'pending', 'failed')" in sql
        assert params == ("student-sub", "dev")


class TestPurchaseCheckoutOwnership:
    def test_course_blocks_when_bundle_paid(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.fetchone_results = [(1,)]  # bundle paid

        assert (
            repo.has_checkout_blocking_ownership(
                "u", product_type="course", course_id=COURSE_ID
            )
            is True
        )

    def test_bundle_blocks_when_bundle_paid(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.fetchone_results = [(1,)]

        assert (
            repo.has_checkout_blocking_ownership("u", product_type="bundle", course_id=None)
            is True
        )


class TestPurchaseReservePending:
    def test_fresh_pending_returns_checkout_in_progress(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.fetchone_results = [(1,)]

        outcome = repo.reserve_pending_checkout(
            "student-sub",
            product_type="course",
            course_id=COURSE_ID,
            amount_minor=5000,
            currency="USD",
            ttl_minutes=30,
        )

        assert outcome == ("checkout_in_progress", None)
        assert not any("INSERT" in sql.upper() for sql, _ in conn.cursor_obj.executions)

    def test_reserve_inserts_pending_course(self) -> None:
        repo, conn = _repo()
        conn.cursor_obj.fetchone_results = [None, ("c0000000-0000-4000-8000-000000000001",)]

        outcome = repo.reserve_pending_checkout(
            "student-sub",
            product_type="course",
            course_id=COURSE_ID,
            amount_minor=5000,
            currency="USD",
            ttl_minutes=30,
        )

        assert outcome == ("reserved", "c0000000-0000-4000-8000-000000000001")
        joined = "\n".join(sql for sql, _ in conn.cursor_obj.executions)
        assert "INSERT" in joined.upper()
        assert "pending" in joined.lower()

    def test_delete_pending_on_rollback(self) -> None:
        repo, conn = _repo()
        repo.delete_pending_checkout(
            "student-sub", product_type="course", course_id=COURSE_ID
        )
        sql, params = conn.cursor_obj.executions[0]
        assert "DELETE" in sql.upper()
        assert "pending" in sql
        assert params[0:3] == ("student-sub", "dev", "course")
