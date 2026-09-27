"""Subscription manage E2E removed in RS-5 (one-time purchases)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="RS-5 removed GET /billing/subscription and POST /billing/cancel-subscription"
)
