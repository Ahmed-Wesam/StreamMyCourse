"""Cognito PreSignUp linking and duplicate-email guards."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Protocol

logger = logging.getLogger(__name__)

_LOG_PREFIX = "cognito_pre_signup"
_FEDERATED_USERNAME_PREFIX = "Google_"
_SIGNUP_DUPLICATE_MESSAGE = (
    "An account with this email already exists. Please sign in with Google."
)


class CognitoIdpClient(Protocol):
    def list_users(self, **kwargs: Any) -> Dict[str, Any]: ...

    def admin_link_provider_for_user(self, **kwargs: Any) -> Dict[str, Any]: ...


def escape_list_users_email_filter(email: str) -> str:
    """Build a ListUsers filter value with quotes and backslashes escaped."""
    escaped = email.replace("\\", "\\\\").replace('"', '\\"')
    return f'email = "{escaped}"'


def google_subject_from_username(user_name: str) -> str | None:
    """Extract Google Cognito subject from federated username (Google_<subject>)."""
    name = (user_name or "").strip()
    if not name.startswith(_FEDERATED_USERNAME_PREFIX):
        return None
    subject = name[len(_FEDERATED_USERNAME_PREFIX) :].strip()
    return subject or None


def is_confirmed_native_user(user: Dict[str, Any]) -> bool:
    """True when the user is a confirmed native (non-federated) pool user."""
    if str(user.get("UserStatus") or "") != "CONFIRMED":
        return False
    username = str(user.get("Username") or "")
    return not username.startswith(_FEDERATED_USERNAME_PREFIX)


def list_users_by_email(client: CognitoIdpClient, user_pool_id: str, email: str) -> List[Dict[str, Any]]:
    response = client.list_users(
        UserPoolId=user_pool_id,
        Filter=escape_list_users_email_filter(email),
        Limit=60,
    )
    users = response.get("Users")
    if not isinstance(users, list):
        return []
    return [u for u in users if isinstance(u, dict)]


def handle_pre_sign_up_external_provider(
    event: Dict[str, Any],
    *,
    client: CognitoIdpClient,
    user_pool_id: str,
) -> Dict[str, Any]:
    request = event.get("request") if isinstance(event.get("request"), dict) else {}
    raw_attrs = request.get("userAttributes")
    attrs: Dict[str, str] = {}
    if isinstance(raw_attrs, dict):
        attrs = {str(k): str(v) if v is not None else "" for k, v in raw_attrs.items()}

    email_verified = str(attrs.get("email_verified", "")).strip().lower()
    if email_verified != "true":
        logger.info("%s external provider signup skipped: email not verified", _LOG_PREFIX)
        return event

    email = str(attrs.get("email", "") or "").strip()
    if not email:
        logger.warning("%s external provider signup missing email; passing through", _LOG_PREFIX)
        return event

    google_subject = google_subject_from_username(str(event.get("userName") or ""))
    if not google_subject:
        logger.warning("%s external provider username is not Google_*; passing through", _LOG_PREFIX)
        return event

    users = list_users_by_email(client, user_pool_id, email)
    native_confirmed = [u for u in users if is_confirmed_native_user(u)]
    if len(native_confirmed) != 1:
        logger.info(
            "%s external provider: no single confirmed native user for email; not linking",
            _LOG_PREFIX,
            extra={"native_confirmed_count": len(native_confirmed)},
        )
        return event

    native_username = str(native_confirmed[0].get("Username") or "").strip()
    if not native_username:
        logger.warning("%s confirmed native user missing Username; not linking", _LOG_PREFIX)
        return event

    client.admin_link_provider_for_user(
        UserPoolId=user_pool_id,
        DestinationUser={
            "ProviderName": "Cognito",
            "ProviderAttributeValue": native_username,
        },
        SourceUser={
            "ProviderName": "Google",
            "ProviderAttributeName": "Cognito_Subject",
            "ProviderAttributeValue": google_subject,
        },
    )
    logger.info(
        "%s linked Google identity to native user",
        _LOG_PREFIX,
        extra={"native_username_prefix": native_username[:8]},
    )
    return event


def handle_pre_sign_up_sign_up(
    event: Dict[str, Any],
    *,
    client: CognitoIdpClient,
    user_pool_id: str,
) -> Dict[str, Any]:
    request = event.get("request") if isinstance(event.get("request"), dict) else {}
    raw_attrs = request.get("userAttributes")
    attrs: Dict[str, str] = {}
    if isinstance(raw_attrs, dict):
        attrs = {str(k): str(v) if v is not None else "" for k, v in raw_attrs.items()}

    email = str(attrs.get("email", "") or "").strip()
    if not email:
        logger.warning("%s native signup missing email; passing through", _LOG_PREFIX)
        return event

    users = list_users_by_email(client, user_pool_id, email)
    if users:
        raise Exception(_SIGNUP_DUPLICATE_MESSAGE)

    return event


def handle_pre_sign_up(
    event: Dict[str, Any],
    *,
    client: CognitoIdpClient,
    user_pool_id: str,
) -> Dict[str, Any]:
    trigger_source = str(event.get("triggerSource") or "")
    if trigger_source == "PreSignUp_ExternalProvider":
        return handle_pre_sign_up_external_provider(event, client=client, user_pool_id=user_pool_id)
    if trigger_source == "PreSignUp_SignUp":
        return handle_pre_sign_up_sign_up(event, client=client, user_pool_id=user_pool_id)
    return event
