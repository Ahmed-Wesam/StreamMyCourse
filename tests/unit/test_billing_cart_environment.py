"""Billing cart_id must follow billing_environment(), not a hardcoded dev segment."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_INTEGRATION_DIR = Path(__file__).resolve().parents[1] / "integration"
if str(_INTEGRATION_DIR) not in sys.path:
    sys.path.insert(0, str(_INTEGRATION_DIR))

from helpers.billing_access import (  # noqa: E402
    billing_environment,
    build_merchant_transaction_id,
)

_USER_SUB = "cognito-sub-for-cart-test"
_PURCHASE_ID = "c0000000-0000-4000-8000-000000000099"


def test_billing_environment_defaults_to_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTEGRATION_BILLING_ENV", raising=False)
    assert billing_environment() == "prod"


def test_merchant_transaction_id_uses_billing_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTEGRATION_BILLING_ENV", "prod")
    cart = build_merchant_transaction_id(
        _USER_SUB, _PURCHASE_ID, product_type="bundle"
    )
    env = billing_environment()
    assert cart == f"v2|{env}|{_USER_SUB}|bundle|{_PURCHASE_ID}"


def test_merchant_transaction_id_reflects_env_override_not_hardcoded_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTEGRATION_BILLING_ENV", "staging")
    cart = build_merchant_transaction_id(
        _USER_SUB, _PURCHASE_ID, product_type="bundle"
    )
    assert cart.startswith("v2|staging|")
    assert "|dev|" not in cart
