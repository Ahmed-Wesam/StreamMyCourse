"""DSQL-5 S6: shared billing integration helpers (preview gate; no secrets logged)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from helpers.billing_access import billing_environment
from helpers.dsql_audit import admin_connect, execute_scalar
from helpers.dsql_preview_access import is_dsql_preview_api_stack

_DEFAULT_REGION = "eu-west-1"
_CATALOG_FN_PREVIEW = "StreamMyCourse-Catalog-dsql"


def resolve_catalog_lambda_function_name() -> str:
    """Catalog function for direct internal billing invoke (preview gate)."""
    override = os.environ.get("INTEGRATION_CATALOG_LAMBDA", "").strip()
    if override:
        return override
    if is_dsql_preview_api_stack():
        return _CATALOG_FN_PREVIEW
    stack = os.environ.get("INTEGRATION_API_STACK", "").strip()
    if stack.endswith("Api-dsql"):
        return _CATALOG_FN_PREVIEW
    if stack.endswith("-prod"):
        return "StreamMyCourse-Catalog-prod"
    return _CATALOG_FN_PREVIEW


def invoke_billing_checkout(
    user_sub: str,
    *,
    product_type: str = "bundle",
    course_id: str | None = None,
    function_name: str | None = None,
) -> dict[str, Any]:
    """Direct ``lambda:InvokeFunction`` for ``billing.checkout`` (D9)."""
    import boto3

    fn = function_name or resolve_catalog_lambda_function_name()
    region = os.environ.get("INTEGRATION_AWS_REGION", _DEFAULT_REGION).strip() or _DEFAULT_REGION
    payload: dict[str, Any] = {
        "internal": "billing.checkout",
        "userSub": user_sub,
        "productType": product_type,
    }
    if course_id:
        payload["courseId"] = course_id
    client = boto3.client("lambda", region_name=region)
    resp = client.invoke(
        FunctionName=fn,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    err = resp.get("FunctionError")
    raw = resp.get("Payload")
    body = json.loads(raw.read()) if raw is not None else {}
    if err:
        raise AssertionError(
            f"billing.checkout invoke failed: FunctionError={err!r} payload={body!r}"
        )
    return body


def invoke_billing_rollback_checkout(
    user_sub: str,
    *,
    product_type: str = "bundle",
    course_id: str | None = None,
) -> dict[str, Any]:
    """Drop a pending checkout row via internal ``billing.rollback_checkout``."""
    import boto3

    fn = resolve_catalog_lambda_function_name()
    region = os.environ.get("INTEGRATION_AWS_REGION", _DEFAULT_REGION).strip() or _DEFAULT_REGION
    payload: dict[str, Any] = {
        "internal": "billing.rollback_checkout",
        "userSub": user_sub,
        "productType": product_type,
    }
    if course_id:
        payload["courseId"] = course_id
    client = boto3.client("lambda", region_name=region)
    resp = client.invoke(
        FunctionName=fn,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    raw = resp.get("Payload")
    return json.loads(raw.read()) if raw is not None else {}


def count_purchases_for_user(user_sub: str) -> int:
    with admin_connect() as conn:
        return int(
            execute_scalar(
                conn,
                "SELECT COUNT(*) FROM app.purchases WHERE user_sub = %s",
                (user_sub,),
            )
            or 0
        )


def count_pending_bundle_checkouts(user_sub: str) -> int:
    env = billing_environment()
    with admin_connect() as conn:
        return int(
            execute_scalar(
                conn,
                """
                SELECT COUNT(*) FROM app.purchases
                WHERE user_sub = %s AND environment = %s
                  AND product_type = 'bundle' AND status = 'pending'
                """,
                (user_sub, env),
            )
            or 0
        )


def insert_pending_bundle_purchase(
    user_sub: str,
    *,
    amount_minor: int | None = None,
    purchase_id: str | None = None,
) -> str:
    pid = purchase_id or str(uuid.uuid4())
    env = billing_environment()
    with admin_connect() as conn:
        if amount_minor is None:
            row = execute_scalar(
                conn,
                "SELECT amount_minor FROM app.bundle_offers WHERE environment = %s LIMIT 1",
                (env,),
            )
            amount_minor = int(row or 150_000)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app.purchases (
                    id, user_sub, environment, product_type, course_id,
                    status, amount_minor, currency
                ) VALUES (%s, %s, %s, 'bundle', NULL, 'pending', %s, 'JOD')
                """,
                (pid, user_sub, env, amount_minor),
            )
        conn.commit()
    return pid


def delete_purchases_for_user(user_sub: str) -> None:
    with admin_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM app.purchases WHERE user_sub = %s", (user_sub,))
        conn.commit()


def delete_webhook_events(provider: str, provider_event_ids: list[str]) -> None:
    if not provider_event_ids:
        return
    with admin_connect() as conn:
        with conn.cursor() as cur:
            for eid in provider_event_ids:
                cur.execute(
                    "DELETE FROM app.payment_webhook_events WHERE provider = %s AND provider_event_id = %s",
                    (provider, eid),
                )
        conn.commit()
