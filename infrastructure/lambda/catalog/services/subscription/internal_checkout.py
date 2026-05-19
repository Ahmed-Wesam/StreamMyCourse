"""Direct Lambda invoke handler for billing.checkout (not API Gateway)."""

from __future__ import annotations

from typing import Any, Dict

from services.subscription.checkout_service import BillingCheckoutService


def _user_sub_from_event(event: Dict[str, Any]) -> str:
    return str(event.get("userSub") or event.get("user_sub") or "").strip()


def handle_internal_billing_checkout(
    event: Dict[str, Any],
    *,
    checkout_service: BillingCheckoutService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    plan_id = str(event.get("planId") or event.get("plan_id") or "").strip()
    if not user_sub:
        raise ValueError("userSub is required for billing.checkout")
    if not plan_id:
        raise ValueError("planId is required for billing.checkout")
    return checkout_service.run_billing_checkout_precheck(user_sub, plan_id)


def handle_internal_billing_rollback(
    event: Dict[str, Any],
    *,
    checkout_service: BillingCheckoutService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for billing.rollback_checkout")
    checkout_service.rollback_billing_checkout_precheck(user_sub)
    return {"rolledBack": True}
