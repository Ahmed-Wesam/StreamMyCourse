"""Direct Lambda invoke handlers for billing manage (not API Gateway)."""

from __future__ import annotations

from typing import Any, Dict

from services.subscription.manage_service import SubscriptionManageService


def _user_sub_from_event(event: Dict[str, Any]) -> str:
    return str(event.get("userSub") or event.get("user_sub") or "").strip()


def handle_internal_billing_cancel_at_period_end(
    event: Dict[str, Any],
    *,
    manage_service: SubscriptionManageService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for billing.cancel_at_period_end")
    return manage_service.cancel_at_period_end(user_sub=user_sub)
