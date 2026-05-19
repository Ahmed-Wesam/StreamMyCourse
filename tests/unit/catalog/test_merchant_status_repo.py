"""W4-P2: RDS read of teacher_merchant_accounts for merchant status."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple
from unittest.mock import MagicMock

import pytest

from services.billing_merchant.repo import MerchantAccountRdsRepository
from services.billing_merchant.service import (
    MerchantStatusService,
    _build_setup_checklist,
    _has_live_profile_id,
    _has_synced_profile_id,
    _is_placeholder_profile_id,
)


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


def _merchant_row(
    *,
    environment: str = "dev",
    provider_profile_id: str = "pt-profile-99",
    payout_ready: bool = True,
) -> Tuple[Any, ...]:
    return (
        environment,
        "teacher-sub",
        "paytabs",
        provider_profile_id,
        payout_ready,
        datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


class TestMerchantAccountRdsRepository:
    def test_get_merchant_account_queries_by_environment(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [_merchant_row()]
        repo = MerchantAccountRdsRepository(lambda: conn)

        row = repo.get_merchant_account(environment="dev")

        assert row is not None
        sql, params = conn.cursor_obj.executions[0]
        assert "teacher_merchant_accounts" in sql
        assert "environment" in sql
        assert params == ("dev",)
        assert row["provider"] == "paytabs"
        assert row["providerProfileId"] == "pt-profile-99"
        assert row["payoutReady"] is True
        assert row["payoutReadyAt"] != ""

    def test_get_merchant_account_returns_none_when_missing(self) -> None:
        conn = FakeConn()
        repo = MerchantAccountRdsRepository(lambda: conn)

        assert repo.get_merchant_account(environment="prod") is None


class TestMerchantProfileIdClassification:
    @pytest.mark.parametrize(
        "profile_id",
        [
            None,
            "",
            "mock-profile",
            "mock-profile-001",
            "placeholder-dev-paytabs-profile-id",
        ],
    )
    def test_placeholder_profile_ids(self, profile_id: str | None) -> None:
        assert _is_placeholder_profile_id(profile_id)
        assert not _has_live_profile_id(profile_id)

    def test_live_profile_id(self) -> None:
        assert not _is_placeholder_profile_id("pt-profile-99")
        assert _has_live_profile_id("pt-profile-99")
        assert _has_synced_profile_id("pt-profile-99")

    def test_placeholder_profile_is_synced_but_not_live(self) -> None:
        assert _has_synced_profile_id("mock-profile-001")
        assert not _has_live_profile_id("mock-profile-001")


class TestMerchantSetupChecklist:
    def test_placeholder_profile_synced_but_account_not_created(self) -> None:
        checklist = _build_setup_checklist(
            {
                "providerProfileId": "mock-profile-001",
                "payoutReady": True,
            }
        )
        assert checklist["paytabsAccountCreated"] is False
        assert checklist["profileIdConfigured"] is True
        assert checklist["testChargeSucceeded"] is False
        assert checklist["payoutMarkedReady"] is True

    def test_live_profile_payout_ready_does_not_imply_test_charge(self) -> None:
        checklist = _build_setup_checklist(
            {
                "providerProfileId": "pt-profile-99",
                "payoutReady": True,
            }
        )
        assert checklist["profileIdConfigured"] is True
        assert checklist["payoutMarkedReady"] is True
        assert checklist["testChargeSucceeded"] is False


class TestMerchantStatusService:
    def test_get_merchant_status_maps_payout_and_profile_from_row(self) -> None:
        repo = MagicMock()
        repo.get_merchant_account.return_value = {
            "provider": "paytabs",
            "providerProfileId": "pt-profile-99",
            "payoutReady": True,
            "payoutReadyAt": "2026-05-01T12:00:00+00:00",
        }
        svc = MerchantStatusService(repo, deployment_environment="dev")

        body = svc.get_merchant_status()

        repo.get_merchant_account.assert_called_once_with(environment="dev")
        assert body["provider"] == "paytabs"
        assert body["providerProfileId"] == "pt-profile-99"
        assert body["payoutReady"] is True
        assert body["payoutReadyAt"] == "2026-05-01T12:00:00+00:00"
        checklist = body["setupChecklist"]
        assert checklist["profileIdConfigured"] is True
        assert checklist["payoutMarkedReady"] is True
        assert checklist["testChargeSucceeded"] is False

    def test_get_merchant_status_placeholder_profile_splits_checklist_flags(self) -> None:
        repo = MagicMock()
        repo.get_merchant_account.return_value = {
            "provider": "paytabs",
            "providerProfileId": "mock-profile-001",
            "payoutReady": False,
            "payoutReadyAt": None,
        }
        svc = MerchantStatusService(repo, deployment_environment="dev")

        checklist = svc.get_merchant_status()["setupChecklist"]

        assert checklist["profileIdConfigured"] is True
        assert checklist["paytabsAccountCreated"] is False

    def test_get_merchant_status_defaults_when_row_missing(self) -> None:
        repo = MagicMock()
        repo.get_merchant_account.return_value = None
        svc = MerchantStatusService(repo, deployment_environment="dev")

        body = svc.get_merchant_status()

        assert body["provider"] == "paytabs"
        assert body["providerProfileId"] is None
        assert body["payoutReady"] is False
        assert body["payoutReadyAt"] is None
        assert all(v is False for v in body["setupChecklist"].values())
