"""Catalog Lambda invoke for billing.checkout precheck (WS6)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

_INTERNAL_CHECKOUT = "billing.checkout"
_INTERNAL_ROLLBACK = "billing.rollback_checkout"


class CatalogInvokeError(Exception):
    """Catalog invoke failed or is not configured."""


def invoke_billing_checkout(
    *,
    user_sub: str,
    plan_id: str,
    catalog_lambda_arn: str,
) -> Dict[str, Any]:
    """Invoke catalog internal billing.checkout; returns blockReason + plan payload."""
    payload = {
        "internal": _INTERNAL_CHECKOUT,
        "userSub": user_sub,
        "planId": plan_id,
    }
    client = boto3.client("lambda")
    try:
        response = client.invoke(
            FunctionName=catalog_lambda_arn,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload).encode("utf-8"),
        )
    except (BotoCoreError, ClientError) as exc:
        logger.exception("catalog_invoke_failed user_sub=%s plan_id=%s", user_sub, plan_id)
        raise CatalogInvokeError("catalog invoke failed") from exc

    status = response.get("StatusCode")
    if status != 200:
        raise CatalogInvokeError(f"catalog invoke status {status!r}")

    function_error = response.get("FunctionError")
    if function_error:
        logger.error(
            "catalog_invoke_function_error user_sub=%s plan_id=%s error=%s",
            user_sub,
            plan_id,
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


def invoke_billing_checkout_rollback(
    *,
    user_sub: str,
    catalog_lambda_arn: str,
) -> None:
    """Best-effort: remove incomplete checkout row after edge could not create HPP session."""
    payload = {
        "internal": _INTERNAL_ROLLBACK,
        "userSub": user_sub,
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
