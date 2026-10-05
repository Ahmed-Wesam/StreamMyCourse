"""Checkout billing contact parsing for HyperPay."""

from __future__ import annotations

import pytest

from domain.checkout_billing import parse_checkout_billing


def test_parse_checkout_billing_accepts_camel_case_fields() -> None:
    contact = parse_checkout_billing(
        {
            "givenName": "Ada",
            "surname": "Lovelace",
            "street": "1 King Hussein St",
            "city": "Amman",
            "state": "Amman",
            "postcode": "11118",
            "country": "jo",
        }
    )
    assert contact.given_name == "Ada"
    assert contact.country == "JO"


def test_parse_checkout_billing_rejects_invalid_country() -> None:
    with pytest.raises(ValueError, match="two-letter"):
        parse_checkout_billing(
            {
                "givenName": "A",
                "surname": "B",
                "street": "1",
                "city": "C",
                "state": "S",
                "postcode": "1",
                "country": "Jordan",
            }
        )
