from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from services.auth.service import UserProfileService
from services.common.errors import HttpError, Unauthorized
from services.common.http import apigw_cognito_claims, json_response
from services.common.runtime_context import update_action

logger = logging.getLogger(__name__)


def handle_users_me(
    event: Dict[str, Any],
    *,
    origin: Optional[str],
    auth_svc: UserProfileService,
) -> Dict[str, Any]:
    # Set action for correlation logging
    update_action("get_users_me")

    claims = apigw_cognito_claims(event)
    sub = str(claims.get("sub", "") or "").strip()
    email = str(claims.get("email", "") or "").strip()
    role = str(claims.get("custom:role") or claims.get("role") or "student").strip()

    try:
        if not sub:
            raise Unauthorized("Authentication required")
        body = auth_svc.get_or_create_profile(user_sub=sub, email=email, role=role)
        return json_response(200, body, origin)
    except HttpError as e:
        # Log expected errors at INFO without stack trace
        logger.info(
            "HTTP error",
            extra={
                "action": "get_users_me",
                "status_code": e.status_code,
                "error_code": e.code,
            },
        )
        return json_response(e.status_code, {"message": e.message, **({"code": e.code} if e.code else {})}, origin)
    except Exception:
        logger.exception("handle_users_me failed", extra={"action": "get_users_me"})
        return json_response(500, {"message": "Internal error", "code": "internal_error"}, origin)
