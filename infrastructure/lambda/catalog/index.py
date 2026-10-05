from __future__ import annotations

import _vendor_bootstrap  # noqa: F401  # MUST be first: prepends _vendor/ to sys.path before repo imports

import logging
import time
from typing import Any, Dict, Optional

from bootstrap import get_cached_aws_deps, lambda_bootstrap, warm_aws_deps_if_needed
from config import load_config, AppConfig
from services.auth.controller import handle_users_me, handle_users_me_patch
from services.auth.session import check_student_session
from services.purchases.controller import (
    handle_get_bundle_offer,
    handle_get_purchases,
    handle_patch_bundle_price,
    handle_patch_course_price,
)
from services.common.http import apigw_routing_path, json_response, options_response, pick_origin
from services.progress.controller import handle_progress_request
from services.common.logging_setup import configure_logging
from services.common.runtime_context import bind_from_lambda_event, clear_request_context, set_request_path
from services.common.internal_invoke import run_internal_handler
from services.course_management.controller import handle as course_management_handle
from services.course_management.kinescope_routing import (
    kinescope_http_routed_on_catalog,
    upload_kind_from_apigw_event,
)
from services.course_management.video_webhooks import handle_kinescope_drm_auth
from services.question_banks.controller import handle_question_banks_request
from services.contact.controller import handle_contact_request
from services.lesson_notes.controller import handle_lesson_notes_request
from services.assignments.controller import handle_assignments_request
from services.certificates.controller import handle_certificates_request
from services.research_team.controller import handle_research_team_request
from services.rate_limit.http import check_rate_limit

logger = logging.getLogger(__name__)

# Configure logging on module load (cold start)
configure_logging()

_student_session_guard_warned = False

_INTERNAL_BILLING_CHECKOUT = "billing.checkout"
_INTERNAL_BILLING_ROLLBACK = "billing.rollback_checkout"
_INTERNAL_BILLING_CHECKOUT_STATUS = "billing.checkout_status"
_INTERNAL_VIDEO_PREPARE = "video.prepare_upload"
_INTERNAL_VIDEO_COMMIT = "video.commit_pending_upload"
_INTERNAL_VIDEO_PREPARE_MARK_READY = "video.prepare_mark_ready"
_INTERNAL_VIDEO_APPLY_MARK_READY = "video.apply_mark_ready"
_INTERNAL_VIDEO_WEBHOOK_STATUS = "video.webhook_status"

_INTERNAL_EVENTS = frozenset(
    {
        _INTERNAL_BILLING_CHECKOUT,
        _INTERNAL_BILLING_ROLLBACK,
        _INTERNAL_BILLING_CHECKOUT_STATUS,
        _INTERNAL_VIDEO_PREPARE,
        _INTERNAL_VIDEO_COMMIT,
        _INTERNAL_VIDEO_PREPARE_MARK_READY,
        _INTERNAL_VIDEO_APPLY_MARK_READY,
        _INTERNAL_VIDEO_WEBHOOK_STATUS,
    }
)


def _rds_config_complete(cfg: AppConfig) -> bool:
    return bool(cfg.db_host and cfg.db_name and cfg.db_secret_arn)


def _handle_internal_billing_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Direct invoke only — not routed via API Gateway."""
    cfg = load_config()
    if not _rds_config_complete(cfg):
        raise RuntimeError(
            "Catalog is not configured: set DB_HOST, DB_NAME, and DB_SECRET_ARN"
        )
    warm_aws_deps_if_needed(cfg)
    deps = get_cached_aws_deps()
    if deps is None:
        raise RuntimeError("Catalog dependencies are not available")
    from services.purchases.internal_checkout import (
        handle_internal_purchase_checkout,
        handle_internal_purchase_checkout_status,
        handle_internal_purchase_rollback,
    )

    internal = event.get("internal")
    if internal == _INTERNAL_BILLING_CHECKOUT:
        return handle_internal_purchase_checkout(
            event, checkout_service=deps.purchase_checkout_service
        )
    if internal == _INTERNAL_BILLING_CHECKOUT_STATUS:
        return handle_internal_purchase_checkout_status(
            event, checkout_service=deps.purchase_checkout_service
        )
    if internal == _INTERNAL_BILLING_ROLLBACK:
        return handle_internal_purchase_rollback(
            event, checkout_service=deps.purchase_checkout_service
        )
    raise ValueError(f"unknown internal billing event: {internal!r}")


def _handle_internal_video_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Direct invoke only — video provider edge upload-url orchestration."""
    from services.course_management.internal_video import (
        handle_internal_video_apply_mark_ready,
        handle_internal_video_commit_pending_upload,
        handle_internal_video_prepare_mark_ready,
        handle_internal_video_prepare_upload,
        handle_internal_video_webhook_status,
    )

    cfg = load_config()
    if not _rds_config_complete(cfg):
        raise RuntimeError(
            "Catalog is not configured: set DB_HOST, DB_NAME, and DB_SECRET_ARN"
        )
    warm_aws_deps_if_needed(cfg)
    deps = get_cached_aws_deps()
    if deps is None or deps.service is None:
        raise RuntimeError("Catalog dependencies are not available")
    internal = event.get("internal")
    if internal == _INTERNAL_VIDEO_PREPARE:
        return run_internal_handler(
            handle_internal_video_prepare_upload,
            event,
            course_service=deps.service,
        )
    if internal == _INTERNAL_VIDEO_COMMIT:
        return run_internal_handler(
            handle_internal_video_commit_pending_upload,
            event,
            course_service=deps.service,
        )
    if internal == _INTERNAL_VIDEO_PREPARE_MARK_READY:
        return run_internal_handler(
            handle_internal_video_prepare_mark_ready,
            event,
            course_service=deps.service,
        )
    if internal == _INTERNAL_VIDEO_APPLY_MARK_READY:
        return run_internal_handler(
            handle_internal_video_apply_mark_ready,
            event,
            course_service=deps.service,
        )
    if internal == _INTERNAL_VIDEO_WEBHOOK_STATUS:
        return run_internal_handler(
            handle_internal_video_webhook_status,
            event,
            course_service=deps.service,
        )
    raise ValueError(f"unknown internal video event: {internal!r}")


def _handle_internal_event(event: Dict[str, Any]) -> Dict[str, Any]:
    internal = event.get("internal")
    if internal in (
        _INTERNAL_BILLING_CHECKOUT,
        _INTERNAL_BILLING_ROLLBACK,
        _INTERNAL_BILLING_CHECKOUT_STATUS,
    ):
        return _handle_internal_billing_event(event)
    if internal in (
        _INTERNAL_VIDEO_PREPARE,
        _INTERNAL_VIDEO_COMMIT,
        _INTERNAL_VIDEO_PREPARE_MARK_READY,
        _INTERNAL_VIDEO_APPLY_MARK_READY,
        _INTERNAL_VIDEO_WEBHOOK_STATUS,
    ):
        return _handle_internal_video_event(event)
    raise ValueError(f"unknown internal event: {internal!r}")


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

        if event.get("internal") in _INTERNAL_EVENTS:
            return _handle_internal_event(event)

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
                auth_repo,
                progress_service,
                question_bank_service,
                purchase_manage_service,
                rate_limit_service,
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
                route_response: Optional[Dict[str, Any]] = None

                global _student_session_guard_warned
                if (
                    auth_repo is not None
                    and not (cfg.student_cognito_client_id or "").strip()
                    and not _student_session_guard_warned
                ):
                    logger.warning(
                        "STUDENT_COGNITO_CLIENT_ID unset; student single-session guard disabled",
                    )
                    _student_session_guard_warned = True

                if method != "OPTIONS" and auth_repo is not None:
                    route_response = check_student_session(
                        event,
                        origin,
                        auth_repo,
                        cfg.student_cognito_client_id,
                    )

                if route_response is None:
                    route_response = check_rate_limit(
                        event,
                        origin,
                        rate_limit_service,
                        method=method,
                        parts=parts,
                    )

                if route_response is None:
                    aws_deps = get_cached_aws_deps()
                    contact_resp: Optional[Dict[str, Any]] = None
                    if aws_deps is not None:
                        contact_resp = handle_contact_request(
                            event,
                            origin=origin,
                            contact_svc=aws_deps.contact_service,
                        )
                    elif method in ("POST", "OPTIONS") and parts == ["contact"]:
                        contact_resp = json_response(
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
                    if contact_resp is not None:
                        route_response = contact_resp

                if route_response is None:
                    qb_resp = None
                    if question_bank_service is not None:
                        qb_resp = handle_question_banks_request(
                            event,
                            origin=origin,
                            qb_svc=question_bank_service,
                        )

                    if qb_resp is not None:
                        route_response = qb_resp
                    elif (
                        len(parts) == 3
                        and parts[0] == "courses"
                        and parts[2] == "progress"
                        and method in ("GET", "OPTIONS")
                    ):
                        route_response = handle_progress_request(
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
                        route_response = handle_progress_request(
                            event,
                            origin=origin,
                            progress_svc=progress_service,
                        )
                    elif (
                        len(parts) == 2
                        and parts[0] == "me"
                        and parts[1] == "activity"
                        and method in ("GET", "OPTIONS")
                    ):
                        route_response = handle_progress_request(
                            event,
                            origin=origin,
                            progress_svc=progress_service,
                        )
                    elif method == "GET" and parts == ["users", "me"]:
                        route_response = handle_users_me(
                            event,
                            origin=origin,
                            auth_svc=auth_service,
                        )
                    elif method == "PATCH" and parts == ["users", "me"]:
                        route_response = handle_users_me_patch(
                            event,
                            origin=origin,
                            auth_svc=auth_service,
                        )
                    elif (
                        method == "GET"
                        and parts == ["billing", "bundle"]
                        and purchase_manage_service is not None
                    ):
                        route_response = handle_get_bundle_offer(
                            event,
                            origin=origin,
                            manage_svc=purchase_manage_service,
                        )
                    elif (
                        method == "PATCH"
                        and parts == ["billing", "bundle"]
                        and purchase_manage_service is not None
                    ):
                        route_response = handle_patch_bundle_price(
                            event,
                            origin=origin,
                            manage_svc=purchase_manage_service,
                        )
                    elif (
                        method == "GET"
                        and parts == ["billing", "purchases"]
                        and purchase_manage_service is not None
                    ):
                        route_response = handle_get_purchases(
                            event,
                            origin=origin,
                            manage_svc=purchase_manage_service,
                        )
                    elif (
                        method == "PATCH"
                        and len(parts) == 4
                        and parts[0] == "billing"
                        and parts[1] == "courses"
                        and parts[3] == "price"
                        and purchase_manage_service is not None
                    ):
                        route_response = handle_patch_course_price(
                            event,
                            origin=origin,
                            course_id=parts[2],
                            manage_svc=purchase_manage_service,
                        )
                    elif method in ("POST", "OPTIONS") and parts == [
                        "webhooks",
                        "kinescope",
                        "drm-auth",
                    ]:
                        route_response = handle_kinescope_drm_auth(
                            event,
                            origin=origin,
                            svc=service,
                        )
                    elif kinescope_http_routed_on_catalog(
                        cfg,
                        method=method,
                        parts=parts,
                        upload_kind=upload_kind_from_apigw_event(event)
                        if method == "POST" and parts == ["upload-url"]
                        else None,
                    ):
                        if method == "OPTIONS":
                            route_response = options_response(origin)
                        else:
                            route_response = json_response(
                                503,
                                {
                                    "message": (
                                        "Kinescope upload, mark-ready, and status webhook routes "
                                        "require the video provider edge Lambda. Redeploy the "
                                        "backend with VideoProviderEdgeLambdaArn wired."
                                    ),
                                    "code": "video_edge_required",
                                },
                                origin,
                            )
                    elif (
                        len(parts) >= 5
                        and parts[0] == "courses"
                        and parts[2] == "lessons"
                        and parts[4] == "notes"
                        and (
                            method == "OPTIONS"
                            or (method in ("GET", "POST") and len(parts) == 5)
                            or (method in ("PATCH", "DELETE") and len(parts) == 6)
                        )
                    ):
                        notes_deps = get_cached_aws_deps()
                        if notes_deps is None or notes_deps.lesson_notes_service is None:
                            if method == "OPTIONS":
                                route_response = options_response(origin)
                            else:
                                route_response = json_response(
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
                            route_response = handle_lesson_notes_request(
                                event,
                                origin=origin,
                                notes_svc=notes_deps.lesson_notes_service,
                            )
                    elif (
                        len(parts) >= 3
                        and parts[0] == "courses"
                        and parts[2] == "assignments"
                        and (
                            method == "OPTIONS"
                            or method in ("GET", "POST", "PATCH", "DELETE")
                        )
                    ):
                        assign_deps = get_cached_aws_deps()
                        if assign_deps is None or assign_deps.assignments_service is None:
                            if method == "OPTIONS":
                                route_response = options_response(origin)
                            else:
                                route_response = json_response(
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
                            route_response = handle_assignments_request(
                                event,
                                origin=origin,
                                assignments_svc=assign_deps.assignments_service,
                            )
                    elif (
                        (
                            (len(parts) >= 2 and parts[0] == "research-team")
                            or (len(parts) >= 2 and parts[0] == "me" and parts[1] == "research-team")
                            or (
                                len(parts) == 3
                                and parts[0] == "courses"
                                and parts[2] == "research-team-requirement"
                            )
                        )
                        and (
                            method == "OPTIONS"
                            or method in ("GET", "POST", "PUT", "PATCH")
                        )
                    ):
                        rt_deps = get_cached_aws_deps()
                        if rt_deps is None:
                            if method == "OPTIONS":
                                route_response = options_response(origin)
                            else:
                                route_response = json_response(
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
                            route_response = handle_research_team_request(
                                event,
                                origin=origin,
                                research_team_svc=rt_deps.research_team_service,
                            )
                    elif (
                        (
                            (len(parts) == 2 and parts[0] == "me" and parts[1] == "certificates")
                            or (len(parts) == 2 and parts[0] == "certificates")
                            or (
                                len(parts) >= 3
                                and parts[0] == "courses"
                                and parts[2] == "certificates"
                            )
                        )
                        and (
                            method == "OPTIONS"
                            or method in ("GET", "POST")
                        )
                    ):
                        cert_deps = get_cached_aws_deps()
                        if cert_deps is None:
                            if method == "OPTIONS":
                                route_response = options_response(origin)
                            else:
                                route_response = json_response(
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
                            route_response = handle_certificates_request(
                                event,
                                origin=origin,
                                certificates_svc=cert_deps.certificates_service,
                            )
                    else:
                        route_response = course_management_handle(
                            event,
                            origin=origin,
                            svc=service,
                            video_bucket=cfg.video_bucket,
                            auth_svc=auth_service,
                        )

                response = route_response

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
