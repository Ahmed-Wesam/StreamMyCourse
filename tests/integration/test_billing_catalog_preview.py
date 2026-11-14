"""DSQL-5 S6: HTTPS catalog billing routes (D8 bundle GET)."""

from __future__ import annotations

import httpx

_JOD_FILS_STEP = 1000


def test_get_billing_bundle_jod_whole_fils(api_base_url: str) -> None:
    with httpx.Client(base_url=api_base_url, timeout=30.0) as client:
        resp = client.get("/billing/bundle")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert str(body.get("currency") or "").upper() == "JOD"
    amount = body.get("amountMinor")
    assert amount is not None
    amount_minor = int(amount)
    assert amount_minor > 0
    assert amount_minor % _JOD_FILS_STEP == 0