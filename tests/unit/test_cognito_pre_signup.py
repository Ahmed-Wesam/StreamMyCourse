"""RS-6 Slice B: Cognito PreSignUp trigger (account linking + duplicate email guard)."""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

_COGNITO_PRE_SIGNUP_SRC = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "infrastructure",
        "lambda",
        "cognito_pre_signup",
    )
)


def _load_pre_signup_module(module_name: str, filename: str):
    path = os.path.join(_COGNITO_PRE_SIGNUP_SRC, filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


_linking_mod = _load_pre_signup_module("linking", "linking.py")
cognito_pre_signup_handler = _load_pre_signup_module(
    "streammycourse_cognito_pre_signup_handler",
    "handler.py",
)
lambda_handler = cognito_pre_signup_handler.lambda_handler
escape_list_users_email_filter = _linking_mod.escape_list_users_email_filter

_POOL_ID = "eu-west-1_TestPool"
_NATIVE_USERNAME = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_GOOGLE_SUBJECT = "117234567890123456789"
_GOOGLE_USERNAME = f"Google_{_GOOGLE_SUBJECT}"
_EMAIL = "student@example.com"


def _external_provider_event(
    *,
    email: str = _EMAIL,
    email_verified: str = "true",
    user_name: str = _GOOGLE_USERNAME,
) -> Dict[str, Any]:
    return {
        "version": "1",
        "triggerSource": "PreSignUp_ExternalProvider",
        "region": "eu-west-1",
        "userPoolId": _POOL_ID,
        "userName": user_name,
        "request": {
            "userAttributes": {
                "email": email,
                "email_verified": email_verified,
            },
        },
        "response": {},
    }


def _sign_up_event(*, email: str = _EMAIL) -> Dict[str, Any]:
    return {
        "version": "1",
        "triggerSource": "PreSignUp_SignUp",
        "region": "eu-west-1",
        "userPoolId": _POOL_ID,
        "userName": email,
        "request": {
            "userAttributes": {
                "email": email,
                "email_verified": "false",
            },
        },
        "response": {},
    }


def _list_user(
    *,
    username: str,
    status: str = "CONFIRMED",
) -> Dict[str, Any]:
    return {
        "Username": username,
        "UserStatus": status,
        "Attributes": [{"Name": "email", "Value": _EMAIL}],
    }


def _make_client(list_users_pages: List[List[Dict[str, Any]]] | None = None) -> MagicMock:
    client = MagicMock()
    pages = list_users_pages if list_users_pages is not None else [[]]

    def _list_users(**kwargs: Any) -> Dict[str, Any]:
        page = pages.pop(0) if pages else []
        return {"Users": page}

    client.list_users.side_effect = _list_users
    return client


@pytest.fixture(autouse=True)
def _user_pool_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("USER_POOL_ID", _POOL_ID)


def test_escape_list_users_email_filter_quotes_and_backslashes() -> None:
    assert escape_list_users_email_filter('a"b\\c') == 'email = "a\\"b\\\\c"'


def test_external_provider_links_confirmed_native_user(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client([[ _list_user(username=_NATIVE_USERNAME, status="CONFIRMED") ]])
    monkeypatch.setattr(cognito_pre_signup_handler, "get_cognito_idp_client", lambda: client)

    event = _external_provider_event()
    out = lambda_handler(event, None)

    client.admin_link_provider_for_user.assert_called_once_with(
        UserPoolId=_POOL_ID,
        DestinationUser={
            "ProviderName": "Cognito",
            "ProviderAttributeValue": _NATIVE_USERNAME,
        },
        SourceUser={
            "ProviderName": "Google",
            "ProviderAttributeName": "Cognito_Subject",
            "ProviderAttributeValue": _GOOGLE_SUBJECT,
        },
    )
    assert out is event
    assert out.get("response", {}).get("autoConfirmUser") is not True
    assert out.get("response", {}).get("autoVerifyEmail") is not True


def test_external_provider_skips_unconfirmed_native_user(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client([[ _list_user(username=_NATIVE_USERNAME, status="UNCONFIRMED") ]])
    monkeypatch.setattr(cognito_pre_signup_handler, "get_cognito_idp_client", lambda: client)

    out = lambda_handler(_external_provider_event(), None)

    client.admin_link_provider_for_user.assert_not_called()
    assert out.get("response", {}).get("autoConfirmUser") is not True


def test_external_provider_skips_when_email_not_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client([[ _list_user(username=_NATIVE_USERNAME, status="CONFIRMED") ]])
    monkeypatch.setattr(cognito_pre_signup_handler, "get_cognito_idp_client", lambda: client)

    out = lambda_handler(_external_provider_event(email_verified="false"), None)

    client.list_users.assert_not_called()
    client.admin_link_provider_for_user.assert_not_called()


def test_sign_up_fails_when_email_already_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client(
        [[ _list_user(username=_GOOGLE_USERNAME, status="CONFIRMED") ]]
    )
    monkeypatch.setattr(cognito_pre_signup_handler, "get_cognito_idp_client", lambda: client)

    event = _sign_up_event()
    with pytest.raises(Exception, match="already exists"):
        lambda_handler(event, None)

    client.admin_link_provider_for_user.assert_not_called()
    assert event.get("response", {}).get("autoConfirmUser") is not True


def test_sign_up_passes_through_for_new_email(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _make_client([[]])
    monkeypatch.setattr(cognito_pre_signup_handler, "get_cognito_idp_client", lambda: client)

    event = _sign_up_event(email="new-user@example.com")
    out = lambda_handler(event, None)

    client.admin_link_provider_for_user.assert_not_called()
    assert out is event
    client.list_users.assert_called_once()
    call_kwargs = client.list_users.call_args.kwargs
    assert call_kwargs["UserPoolId"] == _POOL_ID
    assert call_kwargs["Filter"] == 'email = "new-user@example.com"'
