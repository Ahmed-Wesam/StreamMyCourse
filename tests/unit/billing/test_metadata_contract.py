"""W3-P2b — cart_id metadata contract."""

from __future__ import annotations

import pytest

from domain.metadata import BillingMetadata, EnvironmentMismatchError, parse_cart_metadata

_PLAN_ID = "00000000-0000-4000-8000-000000000099"
_USER_SUB = "cognito-sub-abc"


def test_parse_valid_dev_metadata() -> None:
    cart_id = f"v1|dev|{_USER_SUB}|{_PLAN_ID}"
    meta = parse_cart_metadata(cart_id, "dev")
    assert meta == BillingMetadata(environment="dev", user_sub=_USER_SUB, plan_id=_PLAN_ID)


def test_parse_valid_prod_metadata() -> None:
    cart_id = f"v1|prod|{_USER_SUB}|{_PLAN_ID}"
    meta = parse_cart_metadata(cart_id, "prod")
    assert meta.environment == "prod"


def test_environment_mismatch_raises() -> None:
    cart_id = f"v1|prod|{_USER_SUB}|{_PLAN_ID}"
    with pytest.raises(EnvironmentMismatchError):
        parse_cart_metadata(cart_id, "dev")


def test_invalid_format_raises_value_error() -> None:
    with pytest.raises(ValueError):
        parse_cart_metadata("not-versioned", "dev")

    with pytest.raises(ValueError):
        parse_cart_metadata("v1|dev|only-three", "dev")


def test_parse_v2_course_purchase_metadata() -> None:
    purchase_id = "c0000000-0000-4000-8000-000000000001"
    course_id = "b0000000-0000-4000-8000-000000000001"
    cart_id = f"v2|dev|{_USER_SUB}|course|{course_id}|{purchase_id}"
    meta = parse_cart_metadata(cart_id, "dev")
    assert meta.is_purchase is True
    assert meta.product_type == "course"
    assert meta.course_id == course_id
    assert meta.purchase_id == purchase_id


def test_parse_v2_bundle_purchase_metadata() -> None:
    purchase_id = "c0000000-0000-4000-8000-000000000002"
    cart_id = f"v2|dev|{_USER_SUB}|bundle|{purchase_id}"
    meta = parse_cart_metadata(cart_id, "dev")
    assert meta.product_type == "bundle"
    assert meta.purchase_id == purchase_id
