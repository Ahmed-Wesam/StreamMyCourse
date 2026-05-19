"""W4-P4: billing_sync_merchant_account UPSERT SQL and env param merge."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_MODULE = _ROOT / "scripts" / "billing_sync_merchant_account.py"
_DEPLOY_PAYMENTS = _ROOT / "scripts" / "deploy-payments.sh"


@pytest.fixture(scope="module")
def billing_sync() -> Any:
    assert _MODULE.is_file(), f"missing {_MODULE}"
    spec = importlib.util.spec_from_file_location("billing_sync_merchant_account", _MODULE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_build_upsert_sql_targets_teacher_merchant_accounts(billing_sync: Any) -> None:
    sql = billing_sync.build_upsert_sql()
    assert "INSERT INTO teacher_merchant_accounts" in sql
    assert "ON CONFLICT (environment)" in sql


def test_build_upsert_sql_updates_teacher_sub_profile_and_updated_at_on_conflict(
    billing_sync: Any,
) -> None:
    sql = billing_sync.build_upsert_sql()
    do_update = sql.split("ON CONFLICT", 1)[1]
    assert "teacher_sub = EXCLUDED.teacher_sub" in do_update
    assert "provider_profile_id = EXCLUDED.provider_profile_id" in do_update
    assert "updated_at = NOW()" in do_update


def test_build_upsert_sql_does_not_reset_payout_ready_on_conflict(billing_sync: Any) -> None:
    sql = billing_sync.build_upsert_sql()
    do_update = sql.split("DO UPDATE", 1)[1]
    assert "payout_ready" not in do_update.lower()


def test_merge_params_from_env_reads_billing_env_vars(billing_sync: Any) -> None:
    params = billing_sync.merge_params_from_env(
        {
            "DEPLOYMENT_ENVIRONMENT": "dev",
            "BILLING_TEACHER_SUB": "teacher-sub-abc",
            "PAYTABS_PROFILE_ID": "profile-xyz",
        }
    )
    assert params.environment == "dev"
    assert params.teacher_sub == "teacher-sub-abc"
    assert params.provider_profile_id == "profile-xyz"
    assert params.provider == "paytabs"


def test_merge_params_from_env_strips_whitespace(billing_sync: Any) -> None:
    params = billing_sync.merge_params_from_env(
        {
            "DEPLOYMENT_ENVIRONMENT": "  prod  ",
            "BILLING_TEACHER_SUB": "  sub  ",
            "PAYTABS_PROFILE_ID": "  pid  ",
        }
    )
    assert params.environment == "prod"
    assert params.teacher_sub == "sub"
    assert params.provider_profile_id == "pid"


def test_merge_params_from_env_requires_environment_and_teacher_sub(billing_sync: Any) -> None:
    with pytest.raises(ValueError, match="DEPLOYMENT_ENVIRONMENT"):
        billing_sync.merge_params_from_env(
            {"BILLING_TEACHER_SUB": "sub", "PAYTABS_PROFILE_ID": "p"}
        )
    with pytest.raises(ValueError, match="BILLING_TEACHER_SUB"):
        billing_sync.merge_params_from_env(
            {"DEPLOYMENT_ENVIRONMENT": "dev", "PAYTABS_PROFILE_ID": "p"}
        )


def test_upsert_tuple_order_matches_sql_placeholders(billing_sync: Any) -> None:
    params = billing_sync.merge_params_from_env(
        {
            "DEPLOYMENT_ENVIRONMENT": "dev",
            "BILLING_TEACHER_SUB": "t",
            "PAYTABS_PROFILE_ID": "p",
        }
    )
    tup = billing_sync.upsert_params_tuple(params)
    assert tup == ("dev", "t", "paytabs", "p")


def test_run_upsert_executes_built_sql_with_params(
    billing_sync: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    executed: list[tuple[str, tuple[Any, ...]]] = []

    class _Cursor:
        def execute(self, sql: str, params: tuple[Any, ...]) -> None:
            executed.append((sql, params))

    class _Conn:
        def cursor(self) -> _Cursor:
            return _Cursor()

        def commit(self) -> None:
            pass

    params = billing_sync.merge_params_from_env(
        {
            "DEPLOYMENT_ENVIRONMENT": "dev",
            "BILLING_TEACHER_SUB": "teacher",
            "PAYTABS_PROFILE_ID": "prof",
        }
    )
    billing_sync.run_upsert(_Conn(), params)
    assert len(executed) == 1
    sql, row = executed[0]
    assert sql == billing_sync.build_upsert_sql()
    assert row == ("dev", "teacher", "paytabs", "prof")


def test_deploy_payments_invokes_merchant_sync_when_billing_teacher_sub_set() -> None:
    text = _DEPLOY_PAYMENTS.read_text(encoding="utf-8")
    assert "billing-sync-merchant-account" in text
    idx = text.index("billing-sync-merchant-account")
    before = text[max(0, idx - 400) : idx]
    assert "BILLING_TEACHER_SUB" in before
