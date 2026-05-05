from __future__ import annotations

import _vendor_bootstrap  # noqa: F401  # MUST be first: prepends _vendor/ to sys.path before repo imports

import logging
import time
from typing import Any, Dict

from bootstrap import lambda_bootstrap
from config import load_config
from services.auth.controller import handle_users_me
from services.common.http import apigw_routing_path, json_response, options_response, pick_origin
from services.common.logging_setup import configure_logging
from services.common.runtime_context import bind_from_lambda_event, clear_request_context, set_request_path
from services.course_management.controller import handle as course_management_handle

logger = logging.getLogger(__name__)

# Configure logging on module load (cold start)
configure_logging()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    start_time = time.perf_counter()
    response: Dict[str, Any] = {}
    method = ""
    raw_path = ""

    try:
        # Bind request context for correlation IDs
        bind_from_lambda_event(event=event, lambda_context=context)

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
            cfg, service, auth_service = lambda_bootstrap()

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
                            "message": "Catalog is not configured: TABLE_NAME must be set.",
                            "code": "catalog_unconfigured",
                        },
                        origin,
                    )
            else:
                parts = [p for p in raw_path.split("/") if p]

                if method == "GET" and parts == ["users", "me"]:
                    response = handle_users_me(
                        event,
                        origin=origin,
                        auth_svc=auth_service,
                        auth_enforced=cfg.cognito_auth_enabled,
                    )
                else:
                    response = course_management_handle(
                        event,
                        origin=origin,
                        svc=service,
                        video_bucket=cfg.video_bucket,
                        auth_svc=auth_service,
                        auth_enforced=cfg.cognito_auth_enabled,
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
