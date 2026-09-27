"""Direct Lambda invoke handler for billing.checkout with productType (RS-5)."""

from __future__ import annotations

from typing import Any, Dict

from services.purchases.checkout_service import PurchaseCheckoutService


def _user_sub_from_event(event: Dict[str, Any]) -> str:
    return str(event.get("userSub") or event.get("user_sub") or "").strip()


def _product_type_from_event(event: Dict[str, Any]) -> str:
    return str(event.get("productType") or event.get("product_type") or "").strip().lower()


def _course_id_from_event(event: Dict[str, Any]) -> str | None:
    raw = event.get("courseId") or event.get("course_id")
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def handle_internal_purchase_checkout(
    event: Dict[str, Any],
    *,
    checkout_service: PurchaseCheckoutService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    product_type = _product_type_from_event(event)
    course_id = _course_id_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for billing.checkout")
    if product_type not in ("course", "bundle"):
        raise ValueError("productType must be course or bundle for purchase checkout")
    if product_type == "course" and not course_id:
        raise ValueError("courseId is required when productType is course")
    return checkout_service.run_purchase_checkout_precheck(
        user_sub,
        product_type=product_type,
        course_id=course_id,
    )


def handle_internal_purchase_rollback(
    event: Dict[str, Any],
    *,
    checkout_service: PurchaseCheckoutService,
) -> Dict[str, Any]:
    user_sub = _user_sub_from_event(event)
    product_type = _product_type_from_event(event)
    course_id = _course_id_from_event(event)
    if not user_sub:
        raise ValueError("userSub is required for billing.rollback_checkout")
    if product_type not in ("course", "bundle"):
        raise ValueError("productType must be course or bundle for purchase rollback")
    checkout_service.rollback_purchase_checkout_precheck(
        user_sub,
        product_type=product_type,
        course_id=course_id if product_type == "course" else None,
    )
    return {"rolledBack": True}
