"""Shopper billing contact for HyperPay checkout POST (OPPWA parameters)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_COUNTRY_A2 = re.compile(r"^[A-Z]{2}$")


@dataclass(frozen=True)
class CheckoutBillingContact:
    given_name: str
    surname: str
    street: str
    city: str
    state: str
    postcode: str
    country: str


def parse_checkout_billing(raw: object) -> CheckoutBillingContact:
    if not isinstance(raw, dict):
        raise ValueError("billing is required")

    given_name = str(raw.get("givenName") or raw.get("given_name") or "").strip()
    surname = str(raw.get("surname") or "").strip()
    street = str(raw.get("street") or raw.get("street1") or "").strip()
    city = str(raw.get("city") or "").strip()
    state = str(raw.get("state") or "").strip()
    postcode = str(raw.get("postcode") or raw.get("postCode") or "").strip()
    country = str(raw.get("country") or "").strip().upper()

    missing = [
        name
        for name, value in (
            ("givenName", given_name),
            ("surname", surname),
            ("street", street),
            ("city", city),
            ("state", state),
            ("postcode", postcode),
            ("country", country),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"billing fields required: {', '.join(missing)}")

    if not _COUNTRY_A2.match(country):
        raise ValueError("billing.country must be a two-letter ISO code")

    return CheckoutBillingContact(
        given_name=given_name,
        surname=surname,
        street=street,
        city=city,
        state=state,
        postcode=postcode,
        country=country,
    )
