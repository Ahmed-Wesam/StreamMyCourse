"""Contract: legacy PayTabs merchant status route removed from api-stack (HyperPay slice)."""

from __future__ import annotations

from pathlib import Path


def _api_stack_text() -> str:
    path = Path(__file__).resolve().parents[2] / "infrastructure" / "templates" / "api-stack.yaml"
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_api_stack_no_billing_merchant_status_route() -> None:
    text = _api_stack_text()
    assert "BillingMerchantResource:" not in text
    assert "BillingMerchantStatusResource:" not in text
    assert "BillingMerchantStatusGetMethod:" not in text
    assert "PathPart: merchant" not in text
    assert "/billing/merchant/status" not in text
