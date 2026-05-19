from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.common.errors import HttpError, NotFound, Unauthorized
from services.common.http import apigw_cognito_claims, json_response
from services.common.runtime_context import update_action
from services.subscription.manage_service import SubscriptionManageService
from services.subscription.repo import SubscriptionSummary

logger = logging.getLogger(__name__)


def _format_utc_iso_z(value: datetime) -> str:
    utc = value.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def subscription_summary_to_json(summary: SubscriptionSummary) -> Dict[str, Any]:
    return {
        "status": summary.status,
        "currentPeriodEnd": _format_utc_iso_z(summary.current_period_end),
        "cancelAtPeriodEnd": summary.cancel_at_period_end,
        "canCancel": summary.can_cancel,
        "canReactivate": summary.can_reactivate,
        "nextBillingDate": (
            _format_utc_iso_z(summary.next_billing_date)
            if summary.next_billing_date is not None
            else None
        ),
        "amountMinor": summary.amount_minor,
        "currency": summary.currency,
        "planLabel": summary.plan_label,
        "pastDue": summary.past_due,
    }


def handle_get_subscription(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    manage_svc: SubscriptionManageService,
) -> Dict[str, Any]:
    update_action("get_billing_subscription")

    try:
        claims = apigw_cognito_claims(event)
        user_sub = str(claims.get("sub", "") or "").strip()
        if not user_sub:
            raise Unauthorized("Authentication required")

        summary = manage_svc.get_subscription_summary(user_sub=user_sub)
        if summary is None:
            raise NotFound(
                "No active subscription to manage",
                code="not_subscribed",
            )

        return json_response(200, subscription_summary_to_json(summary), origin)
    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={
                "action": "get_billing_subscription",
                "status_code": e.status_code,
                "error_code": e.code,
            },
        )
        return json_response(
            e.status_code,
            {"message": e.message, **({"code": e.code} if e.code else {})},
            origin,
        )
    except Exception:
        logger.exception(
            "handle_get_subscription failed",
            extra={"action": "get_billing_subscription"},
        )
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )
