from __future__ import annotations

import _vendor_bootstrap  # noqa: F401  # MUST be first: prepends _vendor/ to sys.path before repo imports

import logging
import time
from typing import Any, Dict, Optional

from bootstrap import get_cached_aws_deps, lambda_bootstrap, warm_aws_deps_if_needed
from config import load_config, AppConfig
from services.auth.controller import handle_users_me
from services.billing_merchant.controller import handle_merchant_status
from services.subscription.controller import handle_get_subscription
from services.common.http import apigw_routing_path, json_response, options_response, pick_origin
from services.progress.controller import handle_progress_request
from services.common.logging_setup import configure_logging
from services.common.runtime_context import bind_from_lambda_event, clear_request_context, set_request_path
from services.course_management.controller import handle as course_management_handle
from services.question_banks.controller import handle_question_banks_request

logger = logging.getLogger(__name__)

# Configure logging on module load (cold start)
configure_logging()

_INTERNAL_BILLING_CHECKOUT = "billing.checkout"
_INTERNAL_BILLING_ROLLBACK = "billing.rollback_checkout"
_INTERNAL_BILLING_CANCEL_AT_PERIOD_END = "billing.cancel_at_period_end"


def _rds_config_complete(cfg: AppConfig) -> bool:
    return bool(cfg.db_host and cfg.db_name and cfg.db_secret_arn)


def _handle_internal_billing_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Direct invoke only — not routed via API Gateway."""
    from services.subscription.internal_checkout import (
        handle_internal_billing_checkout,
        handle_internal_billing_rollback,
    )
    from services.subscription.internal_manage import (
        handle_internal_billing_cancel_at_period_end,
    )

    cfg = load_config()
    if not _rds_config_complete(cfg):
        raise RuntimeError(
            "Catalog is not configured: set DB_HOST, DB_NAME, and DB_SECRET_ARN"
        )
    warm_aws_deps_if_needed(cfg)
    deps = get_cached_aws_deps()
    if deps is None:
        raise RuntimeError("Catalog dependencies are not available")
    internal = event.get("internal")
    if internal == _INTERNAL_BILLING_CHECKOUT:
        return handle_internal_billing_checkout(
            event, checkout_service=deps.checkout_service
        )
    if internal == _INTERNAL_BILLING_ROLLBACK:
        return handle_internal_billing_rollback(
            event, checkout_service=deps.checkout_service
        )
    if internal == _INTERNAL_BILLING_CANCEL_AT_PERIOD_END:
        return handle_internal_billing_cancel_at_period_end(
            event, manage_service=deps.subscription_manage_service
        )
    raise ValueError(f"unknown internal billing event: {internal!r}")


def handle_internal_billing_checkout(event: Dict[str, Any]) -> Dict[str, Any]:
    return _handle_internal_billing_event(event)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    start_time = time.perf_counter()
    response: Dict[str, Any] = {}
    method = ""
    raw_path = ""

    try:
        # Bind request context for correlation IDs
        bind_from_lambda_event(event=event, lambda_context=context)

        if event.get("internal") in (
            _INTERNAL_BILLING_CHECKOUT,
            _INTERNAL_BILLING_ROLLBACK,
            _INTERNAL_BILLING_CANCEL_AT_PERIOD_END,
        ):
            return _handle_internal_billing_event(event)

        method = (
            event.get("requestContext", {}).get("http", {}).get("method")
            or event.get("httpMethod")
            or ""
        )

        raw_path = apigw_routing_path(event)
        set_request_path(raw_path)

        cors_cfg = load_config()
        if not cors_cfg.allowed_origins:
            logger.warning(
                "ALLOWED_ORIGINS is empty or unset; refusing requests until CORS allowlist is configured",
            )
            response = json_response(
                503,
                {
                    "message": (
                        "CORS is not configured: set ALLOWED_ORIGINS to a comma-separated "
                        "list of browser origins (use * only for deliberate development)."
                    ),
                    "code": "cors_misconfigured",
                },
                None,
            )
        else:
            (
                cfg,
                service,
                auth_service,
                progress_service,
                question_bank_service,
                merchant_service,
                subscription_manage_service,
            ) = lambda_bootstrap()

            headers = event.get("headers") or {}
            req_origin = headers.get("origin") or headers.get("Origin")
            origin = pick_origin(cfg.allowed_origins, req_origin)

            if service is None or auth_service is None:
                if method == "OPTIONS":
                    response = options_response(origin)
                else:
                    response = json_response(
                        503,
                        {
                            "message": (
                                "Catalog is not configured: set DB_HOST, DB_NAME, and "
                                "DB_SECRET_ARN (deploy the api stack with RdsStackName "
                                "wired to the RDS stack)."
                            ),
                            "code": "catalog_unconfigured",
                        },
                        origin,
                    )
            else:
                parts = [p for p in raw_path.split("/") if p]

                qb_resp = None
                if question_bank_service is not None:
                    qb_resp = handle_question_banks_request(
                        event,
                        origin=origin,
                        qb_svc=question_bank_service,
                    )

                if qb_resp is not None:
                    response = qb_resp
                elif (
                    len(parts) == 3
                    and parts[0] == "courses"
                    and parts[2] == "progress"
                    and method in ("GET", "OPTIONS")
                ):
                    response = handle_progress_request(
                        event,
                        origin=origin,
                        progress_svc=progress_service,
                    )
                elif (
                    len(parts) == 5
                    and parts[0] == "courses"
                    and parts[2] == "lessons"
                    and parts[4] == "progress"
                    and method in ("PUT", "OPTIONS")
                ):
                    response = handle_progress_request(
                        event,
                        origin=origin,
                        progress_svc=progress_service,
                    )
                elif method == "GET" and parts == ["users", "me"]:
                    response = handle_users_me(
                        event,
                        origin=origin,
                        auth_svc=auth_service,
                    )
                elif (
                    method == "GET"
                    and parts == ["billing", "merchant", "status"]
                    and merchant_service is not None
                ):
                    response = handle_merchant_status(
                        event,
                        origin=origin,
                        merchant_svc=merchant_service,
                        billing_teacher_sub=cfg.billing_teacher_sub,
                    )
                elif (
                    method == "GET"
                    and parts == ["billing", "subscription"]
                    and subscription_manage_service is not None
                ):
                    response = handle_get_subscription(
                        event,
                        origin=origin,
                        manage_svc=subscription_manage_service,
                    )
                else:
                    response = course_management_handle(
                        event,
                        origin=origin,
                        svc=service,
                        video_bucket=cfg.video_bucket,
                        auth_svc=auth_service,
                    )

        # Calculate duration and log request completion
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        status_code = response.get("statusCode", 500)

        logger.info(
            "Request completed",
            extra={
                "method": method,
                "path": raw_path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

    finally:
        # Clean up request context
        clear_request_context()

    return response
