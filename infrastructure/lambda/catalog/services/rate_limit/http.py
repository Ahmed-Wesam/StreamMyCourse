"""API Gateway rate-limit middleware (thin adapter over ``RateLimitService``)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Sequence

from services.common.errors import RateLimitStoreError, TooManyRequests
from services.common.http import apigw_cognito_claims, json_response
from services.rate_limit.models import RateLimitContext
from services.rate_limit.service import RateLimitService

logger = logging.getLogger(__name__)


def _source_ip_from_event(event: Dict[str, Any]) -> str:
    rc = event.get("requestContext") or {}
    ident = rc.get("identity")
    if isinstance(ident, dict):
        ip = ident.get("sourceIp")
        if isinstance(ip, str) and ip.strip():
            return ip.strip()
    http = rc.get("http")
    if isinstance(http, dict):
        ip = http.get("sourceIp")
        if isinstance(ip, str) and ip.strip():
            return ip.strip()
    return ""


def _is_webhook_path(parts: Sequence[str]) -> bool:
    return len(parts) >= 1 and parts[0] == "webhooks"


def check_rate_limit(
    event: Dict[str, Any],
    origin: Optional[str],
    rate_limit_svc: Optional[RateLimitService],
    *,
    method: str,
    parts: Sequence[str],
) -> Optional[Dict[str, Any]]:
    """Return an API Gateway response when limited; ``None`` to proceed."""
    if rate_limit_svc is None:
        return None
    if method == "OPTIONS":
        return None
    if _is_webhook_path(parts):
        return None

    ctx = RateLimitContext(
        method=method,
        parts=tuple(parts),
        claims=apigw_cognito_claims(event),
        source_ip=_source_ip_from_event(event),
    )
    try:
        rate_limit_svc.check(ctx)
    except TooManyRequests as exc:
        logger.warning(
            "rate_limit_denied",
            extra={
                "method": method,
                "path_parts": list(parts),
                "retry_after_seconds": exc.retry_after_seconds,
            },
        )
        resp = json_response(
            exc.status_code,
            {"message": exc.message, "code": exc.code},
            origin,
        )
        if exc.retry_after_seconds is not None:
            resp["headers"]["Retry-After"] = str(exc.retry_after_seconds)
        return resp
    except RateLimitStoreError as exc:
        logger.warning(
            "rate_limit_check_failed",
            extra={
                "method": method,
                "path_parts": list(parts),
            },
        )
        return json_response(
            exc.status_code,
            {"message": exc.message, "code": exc.code},
            origin,
        )
    return None
