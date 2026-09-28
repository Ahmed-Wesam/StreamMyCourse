"""Cognito PreSignUp trigger — link verified Google sign-in to existing native users."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import boto3

from linking import handle_pre_sign_up

logger = logging.getLogger(__name__)
_LOG_PREFIX = "cognito_pre_signup"

_cognito_client: Any | None = None


def get_cognito_idp_client() -> Any:
    """Return a cached cognito-idp client (patch in unit tests)."""
    global _cognito_client
    if _cognito_client is None:
        _cognito_client = boto3.client("cognito-idp")
    return _cognito_client


def _load_user_pool_id(event: Dict[str, Any] | None = None) -> str:
    env = str(os.environ.get("USER_POOL_ID") or "").strip()
    if env:
        return env
    if event:
        return str(event.get("userPoolId") or "").strip()
    return ""


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logging.getLogger().setLevel(logging.INFO)
    user_pool_id = _load_user_pool_id(event)
    if not user_pool_id:
        logger.error("%s USER_POOL_ID is not configured", _LOG_PREFIX)
        return event

    return handle_pre_sign_up(
        event,
        client=get_cognito_idp_client(),
        user_pool_id=user_pool_id,
    )
