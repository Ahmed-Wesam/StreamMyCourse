"""domain.period_bounds — monthly period derivation."""

from __future__ import annotations

from domain.period_bounds import ensure_grant_period_bounds


def test_derives_period_end_from_transaction_time() -> None:
    start, end = ensure_grant_period_bounds(
        {"transaction_time": "2026-05-18T12:00:00Z"},
        None,
        None,
    )
    assert start is not None
    assert end is not None
    assert end.startswith("2026-06-")


def test_preserves_explicit_period_end() -> None:
    start, end = ensure_grant_period_bounds(
        {"transaction_time": "2026-05-18T12:00:00Z"},
        "2026-05-01T00:00:00Z",
        "2026-06-01T00:00:00Z",
    )
    assert start == "2026-05-01T00:00:00Z"
    assert end == "2026-06-01T00:00:00Z"
