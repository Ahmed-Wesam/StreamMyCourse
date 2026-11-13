"""RS-5 Slice D — purchase fulfillment mapping (DSQL-5 S3 OCC)."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
_FULFILL_SRC = ROOT / "infrastructure" / "lambda" / "billing_fulfillment"
_DB_TX_PATH = ROOT / "infrastructure/lambda/catalog/services/common/db_tx.py"


def _ensure_db_tx_registered() -> None:
    if "db_tx" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location("db_tx", _DB_TX_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["db_tx"] = mod


_ensure_db_tx_registered()

if str(_FULFILL_SRC) not in sys.path:
    sys.path.insert(0, str(_FULFILL_SRC))

from domain_events import BillingDomainEvent  # noqa: E402
from fulfillment_repo import (  # noqa: E402
    _apply_purchase_update,
    process_event_in_transaction,
)
from models import purchase_fulfillment_for_event  # noqa: E402


def _purchase_event(**overrides: object) -> BillingDomainEvent:
    base = dict(
        event_type="purchase.paid",
        provider="hyperpay",
        provider_event_id="hyperpay:TST1:A",
        environment="dev",
        user_sub="cognito-sub-1",
        plan_id="",
        payload_digest="a" * 64,
        purchase_id="c0000000-0000-4000-8000-000000000001",
        product_type="course",
        amount_minor=50_000,
        currency="JOD",
        provider_tran_ref="TST1",
    )
    base.update(overrides)
    return BillingDomainEvent(**base)  # type: ignore[arg-type]


def _sql_compact(sql: str) -> str:
    return " ".join(sql.lower().split())


def test_purchase_paid_maps_to_paid_status() -> None:
    target = purchase_fulfillment_for_event(_purchase_event())
    assert target.status == "paid"
    assert target.provider_tran_ref == "TST1"


def test_purchase_failed_maps_to_failed_status() -> None:
    target = purchase_fulfillment_for_event(_purchase_event(event_type="purchase.failed"))
    assert target.status == "failed"


def test_purchase_revoked_maps_to_revoked_status() -> None:
    target = purchase_fulfillment_for_event(
        _purchase_event(event_type="purchase.revoked", provider_tran_ref="ORIG-1")
    )
    assert target.status == "revoked"
    assert target.provider_tran_ref == "ORIG-1"


def test_purchase_paid_ipn_error_mentions_jod_not_usd() -> None:
    cur = MagicMock()
    cur.fetchone.side_effect = [("cognito-sub-1",), (50_000, "JOD", "pending")]
    event = _purchase_event(amount_minor=None, currency=None)
    target = purchase_fulfillment_for_event(event)
    with pytest.raises(ValueError, match="JOD amount and currency"):
        _apply_purchase_update(cur, event=event, target=target)


def test_user_lock_runs_before_purchase_for_update_when_user_sub_set() -> None:
    cur = MagicMock()
    fetch_calls: List[int] = []
    executions: List[str] = []

    def track_fetchone() -> tuple[Any, ...]:
        fetch_calls.append(1)
        if len(fetch_calls) == 1:
            return ("cognito-sub-1",)
        return (50_000, "JOD", "pending")

    def track_execute(sql: str, params: Sequence[Any] = ()) -> None:
        executions.append(sql)

    cur.fetchone.side_effect = track_fetchone
    cur.execute = track_execute  # type: ignore[method-assign]
    cur.rowcount = 1
    event = _purchase_event()
    target = purchase_fulfillment_for_event(event)
    _apply_purchase_update(cur, event=event, target=target)

    assert len(fetch_calls) == 2
    assert "users" in _sql_compact(executions[0])
    assert "for update" in _sql_compact(executions[0])
    assert "purchases" in _sql_compact(executions[1])
    assert "for update" in _sql_compact(executions[1])


def test_purchase_uuid_webhook_locks_row_without_user_sub() -> None:
    cur = MagicMock()
    cur.fetchone.return_value = (50_000, "JOD", "pending")
    cur.rowcount = 1
    event = _purchase_event(user_sub="")
    target = purchase_fulfillment_for_event(event)
    updated = _apply_purchase_update(cur, event=event, target=target)
    assert updated is True
    for call in cur.execute.call_args_list:
        assert "users" not in _sql_compact(call.args[0])
    select_sql = cur.execute.call_args_list[0].args[0]
    select_params = cur.execute.call_args_list[0].args[1]
    assert "user_sub" not in select_sql
    assert select_params == (target.purchase_id, "dev")


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    fetchone_results: List[Optional[Tuple[Any, ...]]] = field(default_factory=list)
    rowcount: int = 1

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if self.fetchone_results:
            return self.fetchone_results.pop(0)
        return ("wh-1",)

    def close(self) -> None:
        return None


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0
    autocommit: bool = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


class TestProcessEventOcc:
    def test_webhook_insert_uses_on_conflict_do_nothing(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.fetchone_results = [None]
        event = _purchase_event()
        result = process_event_in_transaction(conn, event)
        assert result.recorded is False
        insert_sql = next(
            sql for sql, _ in conn.cursor_obj.executions if "payment_webhook_events" in sql.lower()
        )
        assert "on conflict (provider, provider_event_id) do nothing" in _sql_compact(insert_sql)

    def test_retries_on_40001_and_inserts_webhook_once(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.fetchone_results = [
            ("wh-1",),
            ("cognito-sub-1",),
            ("wh-1",),
            ("cognito-sub-1",),
            (50_000, "JOD", "pending"),
        ]
        fail_purchase_lock = {"once": True}
        original_execute = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            original_execute(sql, params)
            compact = _sql_compact(sql)
            if (
                fail_purchase_lock["once"]
                and "purchases" in compact
                and "for update" in compact
            ):
                fail_purchase_lock["once"] = False
                err = Exception("serialization failure")
                err.pgcode = "40001"  # type: ignore[attr-defined]
                raise err

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        event = _purchase_event()
        result = process_event_in_transaction(conn, event)

        assert result.recorded is True
        assert conn.rolled_back == 1
        assert conn.committed == 1
        inserts = [
            sql
            for sql, _ in conn.cursor_obj.executions
            if "insert into payment_webhook_events" in _sql_compact(sql)
        ]
        assert len(inserts) == 2

    def test_body_does_not_commit_before_run_transaction(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.fetchone_results = [
            ("wh-1",),
            ("cognito-sub-1",),
            (50_000, "JOD", "pending"),
        ]
        commits_during_execute: List[int] = []
        original_execute = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            commits_during_execute.append(conn.committed)
            original_execute(sql, params)

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]

        process_event_in_transaction(conn, _purchase_event())

        assert all(c == 0 for c in commits_during_execute)
        assert conn.committed == 1
