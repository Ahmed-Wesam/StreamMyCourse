"""Helpers for integration student fixture assumptions (prod seed, bundle, etc.)."""

from __future__ import annotations

import pytest

from helpers.api import ApiClient


def skip_if_integration_student_has_paid_bundle(student_api: ApiClient) -> None:
    """RS-16 prod seed grants ci-student a paid bundle; unenrolled quiz tests need a bare student."""
    resp = student_api.raw.get("/billing/purchases", timeout=30.0)
    if resp.status_code == 404:
        return
    if resp.status_code != 200:
        pytest.skip(
            f"cannot verify bundle state (GET /billing/purchases HTTP {resp.status_code})"
        )
    try:
        payload = resp.json()
    except Exception as exc:
        pytest.skip(f"cannot parse /billing/purchases: {exc!s}")
    if isinstance(payload, list):
        purchases = payload
    elif isinstance(payload, dict):
        raw = payload.get("purchases")
        purchases = raw if isinstance(raw, list) else []
    else:
        pytest.skip("unexpected /billing/purchases payload")
    for row in purchases:
        if not isinstance(row, dict):
            continue
        if row.get("productType") == "bundle" and row.get("status") == "paid":
            pytest.skip(
                "integration student has a paid bundle (prod RS-16 seed); "
                "unenrolled quiz tests require a student without bundle access"
            )
