"""Billing IPN → SQS → RDS fulfillment (WS3). Live PayTabs smoke deferred to WS8."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(
    reason="WS8: requires live PayTabs keys, IPN registration, and dev HTTPS API",
)


def test_billing_ipn_grants_subscription_on_dev() -> None:
    """Placeholder for end-to-end: subscribe IPN → payment_webhook_events + user_subscriptions."""
    raise NotImplementedError("Enable in WS8 when PayTabs test profile is available")
