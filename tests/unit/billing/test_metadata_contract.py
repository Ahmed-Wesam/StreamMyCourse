"""W3-P2b — cart_id metadata contract (v2 purchases)."""

from __future__ import annotations

import pytest

from domain.metadata import BillingMetadata, EnvironmentMismatchError, parse_cart_metadata

_USER_SUB = "cognito-sub-abc"


def test_environment_mismatch_raises() -> None:
    purchase_id = "c0000000-0000-4000-8000-000000000001"
    course_id = "b0000000-0000-4000-8000-000000000001"
    cart_id = f"v2|prod|{_USER_SUB}|course|{course_id}|{purchase_id}"
    with pytest.raises(EnvironmentMismatchError):
        parse_cart_metadata(cart_id, "dev")


def test_invalid_format_raises_value_error() -> None:
    with pytest.raises(ValueError):
        parse_cart_metadata("not-versioned", "dev")

    with pytest.raises(ValueError):
        parse_cart_metadata("v1|dev|legacy|plan", "dev")


def test_parse_v2_course_purchase_metadata() -> None:
    purchase_id = "c0000000-0000-4000-8000-000000000001"
    course_id = "b0000000-0000-4000-8000-000000000001"
    cart_id = f"v2|dev|{_USER_SUB}|course|{course_id}|{purchase_id}"
    meta = parse_cart_metadata(cart_id, "dev")
    assert meta == BillingMetadata(
        environment="dev",
        user_sub=_USER_SUB,
        product_type="course",
        course_id=course_id,
        purchase_id=purchase_id,
    )
    assert meta.is_purchase is True


def test_parse_v2_bundle_purchase_metadata() -> None:
    purchase_id = "c0000000-0000-4000-8000-000000000002"
    cart_id = f"v2|dev|{_USER_SUB}|bundle|{purchase_id}"
    meta = parse_cart_metadata(cart_id, "dev")
    assert meta.product_type == "bundle"
    assert meta.purchase_id == purchase_id


def test_bank_safe_merchant_transaction_id_is_purchase_uuid() -> None:
    from domain.metadata import bank_safe_merchant_transaction_id

    purchase_id = "C0000000-0000-4000-8000-000000000001"
    merchant_tx = bank_safe_merchant_transaction_id(purchase_id)
    assert merchant_tx == "c0000000-0000-4000-8000-000000000001"
    assert len(merchant_tx) <= 41
    assert "|" not in merchant_tx


def test_bank_safe_merchant_transaction_id_rejects_cart_string() -> None:
    from domain.metadata import bank_safe_merchant_transaction_id

    with pytest.raises(ValueError):
        bank_safe_merchant_transaction_id(
            "v2|prod|cognito-sub|course|b0000000-0000-4000-8000-000000000001|"
            "c0000000-0000-4000-8000-000000000001"
        )
