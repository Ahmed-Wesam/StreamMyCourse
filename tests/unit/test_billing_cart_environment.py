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
    build_mock_ipn_activated,
    seed_plan_id,
)

_USER_SUB = "cognito-sub-for-cart-test"


def test_billing_environment_defaults_to_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("INTEGRATION_BILLING_ENV", raising=False)
    assert billing_environment() == "prod"


def test_build_mock_ipn_activated_cart_id_uses_billing_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTEGRATION_BILLING_ENV", "prod")
    body = build_mock_ipn_activated(_USER_SUB)
    env = billing_environment()
    assert body["cart_id"] == f"v1|{env}|{_USER_SUB}|{seed_plan_id(env)}"


def test_build_mock_ipn_activated_cart_id_reflects_env_override_not_hardcoded_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("INTEGRATION_BILLING_ENV", "staging")
    body = build_mock_ipn_activated(_USER_SUB)
    assert body["cart_id"].startswith("v1|staging|")
    assert "|dev|" not in body["cart_id"]
