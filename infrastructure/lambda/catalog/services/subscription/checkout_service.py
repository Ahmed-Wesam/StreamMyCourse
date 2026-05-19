"""Billing checkout precheck (internal catalog invoke only; no PayTabs HTTP)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.subscription.repo import SubscriptionRdsRepository

BlockReason = Optional[str]  # None | already_subscribed | checkout_in_progress

# Abandoned incomplete rows older than this may start a new checkout (review fix).
INCOMPLETE_CHECKOUT_TTL_MINUTES = 30


class BillingCheckoutService:
    """Gate order: in-period access block → stale incomplete clear → fresh incomplete block → reserve."""

    def __init__(self, subscription_repo: SubscriptionRdsRepository) -> None:
        self._repo = subscription_repo

    def run_billing_checkout_precheck(
        self, user_sub: str, plan_id: str
    ) -> Dict[str, Any]:
        if self._repo.has_checkout_blocking_subscription(user_sub):
            return {"blockReason": "already_subscribed"}
        plan = self._repo.get_subscription_plan_for_checkout(plan_id)
        if plan is None:
            raise ValueError(f"subscription plan not found: {plan_id}")
        reservation = self._repo.reserve_incomplete_checkout(
            user_sub,
            plan_id,
            ttl_minutes=INCOMPLETE_CHECKOUT_TTL_MINUTES,
        )
        if reservation == "checkout_in_progress":
            return {"blockReason": "checkout_in_progress"}
        return {"blockReason": None, "plan": plan}

    def rollback_billing_checkout_precheck(self, user_sub: str) -> None:
        """Remove incomplete reservation when edge could not return a redirect URL."""
        self._repo.delete_incomplete_checkout(user_sub)
