"""Subscription manage read model (WS7 GET /billing/subscription)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.subscription.repo import SubscriptionRdsRepository, SubscriptionSummary


def _format_utc_iso_z(value: datetime) -> str:
    utc = value.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class SubscriptionManageService:
    def __init__(self, subscription_repo: SubscriptionRdsRepository) -> None:
        self._subscription_repo = subscription_repo

    def get_subscription_summary(self, *, user_sub: str) -> Optional[SubscriptionSummary]:
        return self._subscription_repo.get_subscription_summary(user_sub)

    def cancel_at_period_end(self, *, user_sub: str) -> Dict[str, Any]:
        result = self._subscription_repo.cancel_subscription_at_period_end(user_sub)
        if result.outcome == "ok" and result.current_period_end is not None:
            return {
                "status": "canceled",
                "cancelAtPeriodEnd": True,
                "currentPeriodEnd": _format_utc_iso_z(result.current_period_end),
            }
        if result.outcome == "already_canceled":
            return {"errorCode": "already_canceled"}
        if result.outcome == "not_subscribed":
            return {"errorCode": "not_subscribed"}
        return {"errorCode": "cannot_cancel"}

    def reactivate_prepare(self, *, user_sub: str) -> Dict[str, Any]:
        result = self._subscription_repo.reactivate_prepare(user_sub)
        if result.outcome == "ok":
            payload: Dict[str, Any] = {}
            if result.provider_subscription_id:
                payload["providerSubscriptionId"] = result.provider_subscription_id
            return payload
        if result.outcome == "not_subscribed":
            return {"errorCode": "not_subscribed"}
        return {"errorCode": "cannot_reactivate"}

    def reactivate(self, *, user_sub: str) -> Dict[str, Any]:
        result = self._subscription_repo.reactivate_subscription(user_sub)
        if result.outcome == "ok" and result.current_period_end is not None:
            return {
                "status": "active",
                "cancelAtPeriodEnd": False,
                "currentPeriodEnd": _format_utc_iso_z(result.current_period_end),
            }
        if result.outcome == "not_subscribed":
            return {"errorCode": "not_subscribed"}
        return {"errorCode": "cannot_reactivate"}
