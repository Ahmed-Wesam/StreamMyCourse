"""Student single-session: Pre Token Generation bump and refresh deny."""

from __future__ import annotations

import logging
from typing import Any, Dict
from uuid import uuid4

from repo import (
    get_cached_connection_factory,
    get_student_active_session_id,
    mirror_student_active_session_attribute,
    set_student_active_session_id,
)
from sync_config import SyncConfig

logger = logging.getLogger(__name__)
_LOG_PREFIX = "cognito_user_profile_sync.session"


class StudentSessionSupersededError(Exception):
    """Raised when refresh presents a session id that no longer matches RDS."""


def deny_stale_student_refresh(
    *,
    presented_session_id: str,
    active_session_id: str,
) -> None:
    """Fail closed when the client-presented session does not match RDS authority."""
    presented = (presented_session_id or "").strip()
    active = (active_session_id or "").strip()
    if presented != active:
        raise StudentSessionSupersededError(
            "student refresh session superseded (client_metadata_session_id_vs_rds_active)"
        )


def _client_id_from_event(event: Dict[str, Any]) -> str:
    caller = event.get("callerContext")
    if not isinstance(caller, dict):
        return ""
    return str(caller.get("clientId") or "").strip()


def _user_sub_from_event(event: Dict[str, Any]) -> str:
    request = event.get("request")
    if not isinstance(request, dict):
        return ""
    raw_attrs = request.get("userAttributes")
    if not isinstance(raw_attrs, dict):
        return ""
    return str(raw_attrs.get("sub") or "").strip()


def _request_client_metadata(event: Dict[str, Any]) -> Dict[str, str]:
    request = event.get("request")
    if not isinstance(request, dict):
        return {}
    raw = request.get("clientMetadata")
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) if v is not None else "" for k, v in raw.items()}


def _is_student_client(event: Dict[str, Any], cfg: SyncConfig) -> bool:
    student_client_id = (cfg.student_client_id or "").strip()
    if not student_client_id:
        return False
    return _client_id_from_event(event) == student_client_id


def _inject_student_session_claim(event: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    response = event.setdefault("response", {})
    if not isinstance(response, dict):
        response = {}
        event["response"] = response
    claims_override = response.setdefault("claimsOverrideDetails", {})
    if not isinstance(claims_override, dict):
        claims_override = {}
        response["claimsOverrideDetails"] = claims_override
    claims = claims_override.setdefault("claimsToAddOrOverride", {})
    if not isinstance(claims, dict):
        claims = {}
        claims_override["claimsToAddOrOverride"] = claims
    claims["student_session_id"] = session_id
    return event


def _bump_student_session(event: Dict[str, Any], cfg: SyncConfig) -> str:
    user_sub = _user_sub_from_event(event)
    if not user_sub:
        raise RuntimeError("missing sub for student session bump")
    if not cfg.db_secret_arn or not cfg.db_host:
        raise RuntimeError("misconfigured DB for student session bump")

    new_session = str(uuid4())
    factory = get_cached_connection_factory(cfg)
    set_student_active_session_id(factory, user_sub=user_sub, session_id=new_session)
    user_pool_id = str(event.get("userPoolId") or "").strip()
    user_name = str(event.get("userName") or "").strip()
    if not user_pool_id or not user_name:
        raise RuntimeError("missing userPoolId/userName for Cognito session mirror")
    try:
        mirror_student_active_session_attribute(
            user_pool_id=user_pool_id,
            user_name=user_name,
            session_id=new_session,
        )
    except Exception:
        logger.exception(
            "%s Cognito attribute mirror failed after RDS bump",
            _LOG_PREFIX,
            extra={"user_sub_prefix": user_sub[:8]},
        )
        raise
    return new_session


def handle_pre_token_generation(event: Dict[str, Any], cfg: SyncConfig) -> Dict[str, Any]:
    """Route Pre Token events: student session bump/deny; teacher pass-through."""
    if not _is_student_client(event, cfg):
        return event

    trigger_source = str(event.get("triggerSource") or "")

    if trigger_source == "TokenGeneration_RefreshTokens":
        metadata = _request_client_metadata(event)
        presented = str(metadata.get("student_session_id") or "").strip()
        user_sub = _user_sub_from_event(event)
        if not user_sub:
            raise StudentSessionSupersededError("missing sub on student refresh")

        factory = get_cached_connection_factory(cfg)
        active = get_student_active_session_id(factory, user_sub=user_sub)
        if not active.strip():
            request = event.get("request")
            if isinstance(request, dict):
                raw_attrs = request.get("userAttributes")
                if isinstance(raw_attrs, dict):
                    active = str(
                        raw_attrs.get("custom:student_active_session_id") or ""
                    ).strip()

        deny_stale_student_refresh(
            presented_session_id=presented,
            active_session_id=active,
        )
        return _inject_student_session_claim(event, active)

    if trigger_source.startswith("TokenGeneration_"):
        session_id = _bump_student_session(event, cfg)
        return _inject_student_session_claim(event, session_id)

    return event
