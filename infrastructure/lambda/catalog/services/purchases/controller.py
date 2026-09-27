from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Any, Dict, Optional

from services.common.errors import HttpError, Unauthorized
from services.common.http import apigw_cognito_claims, json_response
from services.common.runtime_context import update_action
from services.purchases.manage_service import PurchaseManageService
from services.purchases.models import PurchaseRecord

logger = logging.getLogger(__name__)


def _format_utc_iso_z(value: Any) -> str:
    from datetime import datetime

    if not isinstance(value, datetime):
        return str(value)
    utc = value.astimezone(timezone.utc)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def purchase_record_to_json(record: PurchaseRecord) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "id": record.id,
        "productType": record.product_type,
        "status": record.status,
        "amountMinor": record.amount_minor,
        "currency": record.currency,
        "createdAt": _format_utc_iso_z(record.created_at),
    }
    if record.course_id is not None:
        body["courseId"] = record.course_id
    return body


def _parse_amount_minor(body: Dict[str, Any]) -> int:
    raw = body.get("amountMinor", body.get("amount_minor"))
    if raw is None:
        raise ValueError("amountMinor is required")
    amount = int(raw)
    if amount <= 0:
        raise ValueError("amountMinor must be positive")
    return amount


def handle_get_bundle_offer(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    manage_svc: PurchaseManageService,
) -> Dict[str, Any]:
    update_action("get_billing_bundle")
    try:
        offer = manage_svc.get_public_bundle_offer()
        return json_response(
            200,
            {"amountMinor": offer.amount_minor, "currency": offer.currency},
            origin,
        )
    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={
                "action": "get_billing_bundle",
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
        logger.exception("handle_get_bundle_offer failed", extra={"action": "get_billing_bundle"})
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )


def handle_get_purchases(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    manage_svc: PurchaseManageService,
) -> Dict[str, Any]:
    update_action("get_billing_purchases")
    try:
        claims = apigw_cognito_claims(event)
        user_sub = str(claims.get("sub", "") or "").strip()
        if not user_sub:
            raise Unauthorized("Authentication required")
        records = manage_svc.list_purchases_for_user(user_sub)
        return json_response(
            200,
            {"purchases": [purchase_record_to_json(r) for r in records]},
            origin,
        )
    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={
                "action": "get_billing_purchases",
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
        logger.exception("handle_get_purchases failed", extra={"action": "get_billing_purchases"})
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )


def handle_patch_bundle_price(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    manage_svc: PurchaseManageService,
) -> Dict[str, Any]:
    update_action("patch_billing_bundle_price")
    try:
        claims = apigw_cognito_claims(event)
        caller_sub = str(claims.get("sub", "") or "").strip()
        if not caller_sub:
            raise Unauthorized("Authentication required")
        raw_body = event.get("body") or "{}"
        body = json.loads(raw_body) if isinstance(raw_body, str) else dict(raw_body)
        amount_minor = _parse_amount_minor(body)
        offer = manage_svc.set_bundle_price(caller_sub=caller_sub, amount_minor=amount_minor)
        return json_response(
            200,
            {"amountMinor": offer.amount_minor, "currency": offer.currency},
            origin,
        )
    except ValueError as e:
        return json_response(
            400,
            {"message": str(e), "code": "bad_request"},
            origin,
        )
    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={
                "action": "patch_billing_bundle_price",
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
            "handle_patch_bundle_price failed",
            extra={"action": "patch_billing_bundle_price"},
        )
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )


def handle_patch_course_price(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    course_id: str,
    manage_svc: PurchaseManageService,
) -> Dict[str, Any]:
    update_action("patch_billing_course_price")
    try:
        claims = apigw_cognito_claims(event)
        caller_sub = str(claims.get("sub", "") or "").strip()
        if not caller_sub:
            raise Unauthorized("Authentication required")
        role = str(claims.get("custom:role") or claims.get("role") or "").strip()
        raw_body = event.get("body") or "{}"
        body = json.loads(raw_body) if isinstance(raw_body, str) else dict(raw_body)
        amount_minor = _parse_amount_minor(body)
        payload = manage_svc.set_course_price(
            course_id=course_id,
            caller_sub=caller_sub,
            role=role,
            amount_minor=amount_minor,
        )
        return json_response(200, payload, origin)
    except ValueError as e:
        return json_response(
            400,
            {"message": str(e), "code": "bad_request"},
            origin,
        )
    except HttpError as e:
        logger.info(
            "HTTP error",
            extra={
                "action": "patch_billing_course_price",
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
            "handle_patch_course_price failed",
            extra={"action": "patch_billing_course_price"},
        )
        return json_response(
            500,
            {"message": "Internal error", "code": "internal_error"},
            origin,
        )
