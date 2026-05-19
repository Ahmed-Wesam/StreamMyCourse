from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.billing_merchant.service import MerchantStatusService
from services.common.errors import Forbidden, HttpError
from services.common.http import apigw_cognito_claims, json_response
from services.common.runtime_context import update_action

logger = logging.getLogger(__name__)


def handle_merchant_status(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    merchant_svc: MerchantStatusService,
    billing_teacher_sub: str,
) -> Dict[str, Any]:
    update_action("get_billing_merchant_status")

    try:
        teacher_sub = (billing_teacher_sub or "").strip()
        if not teacher_sub:
            raise ServiceUnavailableBillingUnconfigured()

        claims = apigw_cognito_claims(event)
        caller_sub = str(claims.get("sub", "") or "").strip()
        if caller_sub != teacher_sub:
            raise Forbidden("Forbidden")

        body = merchant_svc.get_merchant_status()
        return json_response(200, body, origin)
    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={
                "action": "get_billing_merchant_status",
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
            "handle_merchant_status failed",
            extra={"action": "get_billing_merchant_status"},
        )
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )


class ServiceUnavailableBillingUnconfigured(HttpError):
    def __init__(self) -> None:
        super().__init__(
            503,
            "Billing is not configured",
            code="billing_unconfigured",
        )
