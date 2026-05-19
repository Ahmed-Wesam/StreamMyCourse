"""W7-P4 — MockPayTabsAdapter cancel/resume are no-ops (no outbound HTTP)."""

from __future__ import annotations

from providers.mock_adapter import MockPayTabsAdapter


def test_mock_cancel_agreement_no_op() -> None:
    adapter = MockPayTabsAdapter()
    adapter.cancel_agreement("agreement-1")


def test_mock_resume_agreement_no_op() -> None:
    adapter = MockPayTabsAdapter()
    adapter.resume_agreement("agreement-1")
