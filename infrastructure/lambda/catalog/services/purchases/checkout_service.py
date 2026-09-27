"""Purchase checkout precheck (internal catalog invoke; no PayTabs HTTP)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from services.purchases.repo import PurchaseRdsRepository

BlockReason = Optional[str]  # None | already_owned | checkout_in_progress

INCOMPLETE_CHECKOUT_TTL_MINUTES = 30


class PurchaseCheckoutService:
    """Gate order: ownership block → reserve pending purchase with TTL."""

    def __init__(self, purchase_repo: PurchaseRdsRepository) -> None:
        self._repo = purchase_repo

    def run_purchase_checkout_precheck(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None = None,
    ) -> Dict[str, Any]:
        normalized_type = (product_type or "").strip().lower()
        if normalized_type not in ("course", "bundle"):
            raise ValueError(f"unsupported productType: {product_type!r}")

        if self._repo.has_checkout_blocking_ownership(
            user_sub,
            product_type=normalized_type,
            course_id=course_id,
        ):
            return {"blockReason": "already_owned"}

        if normalized_type == "course":
            product = self._repo.get_course_price_for_checkout(str(course_id or ""))
            if product is None:
                raise ValueError(f"course not found or has no price: {course_id!r}")
        else:
            offer = self._repo.get_bundle_offer()
            if offer is None:
                raise ValueError("bundle offer not configured for this environment")
            product = {
                "amount_minor": offer.amount_minor,
                "currency": offer.currency,
                "product_type": "bundle",
            }

        reservation_status, purchase_id = self._repo.reserve_pending_checkout(
            user_sub,
            product_type=normalized_type,
            course_id=course_id if normalized_type == "course" else None,
            amount_minor=int(product["amount_minor"]),
            currency=str(product.get("currency") or "USD"),
            ttl_minutes=INCOMPLETE_CHECKOUT_TTL_MINUTES,
        )
        if reservation_status == "checkout_in_progress":
            return {"blockReason": "checkout_in_progress"}
        if purchase_id:
            product = {**product, "purchase_id": purchase_id}
        return {"blockReason": None, "product": product}

    def rollback_purchase_checkout_precheck(
        self,
        user_sub: str,
        *,
        product_type: str,
        course_id: str | None = None,
    ) -> None:
        """Remove pending reservation when edge could not return a redirect URL."""
        normalized_type = (product_type or "").strip().lower()
        self._repo.delete_pending_checkout(
            user_sub,
            product_type=normalized_type,
            course_id=course_id if normalized_type == "course" else None,
        )
