"""Catalog Lambda invoke for billing.checkout precheck (WS6 + RS-5 purchases)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

_INTERNAL_CHECKOUT = "billing.checkout"
_INTERNAL_ROLLBACK = "billing.rollback_checkout"
_INTERNAL_CHECKOUT_STATUS = "billing.checkout_status"
class CatalogInvokeError(Exception):
    """Catalog invoke failed or is not configured."""


def _invoke_catalog_internal(
    *,
    internal: str,
    user_sub: str,
    catalog_lambda_arn: str,
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "internal": internal,
        "userSub": user_sub,
    }
    if extra:
        payload.update(extra)
    client = boto3.client("lambda")
    try:
        response = client.invoke(
            FunctionName=catalog_lambda_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception(
            "catalog_invoke_failed user_sub=%s internal=%s",
            user_sub,
            internal,
        )
        raise CatalogInvokeError("catalog invoke failed") from exc

    status = response.get("StatusCode")
    if status != 200:
        raise CatalogInvokeError(f"catalog invoke status {status!r}")

    function_error = response.get("FunctionError")
    if function_error:
        logger.error(
            "catalog_invoke_function_error user_sub=%s internal=%s error=%s",
            user_sub,
            internal,
            function_error,
        )
        raise CatalogInvokeError(f"catalog function error: {function_error}")

    raw_payload = response.get("Payload")
    if raw_payload is None:
        raise CatalogInvokeError("catalog invoke returned no payload")

    body = raw_payload.read()
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise CatalogInvokeError("catalog invoke returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise CatalogInvokeError("catalog invoke returned non-object payload")

    return parsed


def invoke_billing_checkout(
    *,
    user_sub: str,
    product_type: str,
    course_id: str | None,
    catalog_lambda_arn: str,
) -> Dict[str, Any]:
    """Invoke catalog internal billing.checkout for one-time purchase precheck."""
    extra: Dict[str, Any] = {"productType": product_type}
    if course_id:
        extra["courseId"] = course_id
    return _invoke_catalog_internal(
        internal=_INTERNAL_CHECKOUT,
        user_sub=user_sub,
        catalog_lambda_arn=catalog_lambda_arn,
        extra=extra,
    )


def invoke_billing_checkout_status(
    *,
    user_sub: str,
    purchase_id: str,
    amount_minor: int | None,
    currency: str | None,
    catalog_lambda_arn: str,
) -> Dict[str, Any]:
    """Verify pending purchase belongs to user before returning checkout poll status."""
    extra: Dict[str, Any] = {"purchaseId": purchase_id}
    if amount_minor is not None:
        extra["amountMinor"] = amount_minor
    if currency:
        extra["currency"] = currency
    return _invoke_catalog_internal(
        internal=_INTERNAL_CHECKOUT_STATUS,
        user_sub=user_sub,
        catalog_lambda_arn=catalog_lambda_arn,
        extra=extra,
    )


def invoke_billing_checkout_rollback(
    *,
    user_sub: str,
    product_type: str,
    course_id: str | None,
    catalog_lambda_arn: str,
) -> None:
    """Best-effort: remove incomplete checkout row after edge could not create HPP session."""
    extra: Dict[str, Any] = {"productType": product_type}
    if course_id:
        extra["courseId"] = course_id
    payload = {
        "internal": _INTERNAL_ROLLBACK,
        "userSub": user_sub,
        **extra,
    }
    client = boto3.client("lambda")
    try:
        response = client.invoke(
            FunctionName=catalog_lambda_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
    except (BotoCoreError, ClientError) as exc:
        logger.warning(
            "catalog_rollback_invoke_failed user_sub=%s",
            user_sub,
            exc_info=exc,
        )
        return

    status = response.get("StatusCode")
    if status != 200 or response.get("FunctionError"):
        logger.warning(
            "catalog_rollback_invoke_error user_sub=%s status=%s function_error=%s",
            user_sub,
            status,
            response.get("FunctionError"),
        )
