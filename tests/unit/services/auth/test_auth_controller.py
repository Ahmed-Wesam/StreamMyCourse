from __future__ import annotations

import json
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from services.auth.controller import handle_users_me
from services.common.errors import BadRequest, HttpError


def _body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def test_handle_users_me_returns_401_when_missing_sub(monkeypatch, make_lambda_event) -> None:
    evt = make_lambda_event(method="GET", path="/users/me")
    monkeypatch.setattr("services.auth.controller._claims_dict", lambda *a, **k: {})

    resp = handle_users_me(
        evt,
        origin="*",
        auth_svc=MagicMock(),
    )
    assert resp["statusCode"] == 401
    assert _body(resp)["code"] == "unauthorized"


def test_handle_users_me_prefers_custom_role_over_role(monkeypatch, make_lambda_event) -> None:
    evt = make_lambda_event(method="GET", path="/users/me")
    monkeypatch.setattr(
        "services.auth.controller._claims_dict",
        lambda *a, **k: {"sub": "u1", "email": "a@b.com", "custom:role": "teacher", "role": "student"},
    )
    auth_svc = MagicMock()
    auth_svc.get_or_create_profile.return_value = {"ok": True}

    resp = handle_users_me(
        evt,
        origin="*",
        auth_svc=auth_svc,
    )

    assert resp["statusCode"] == 200
    auth_svc.get_or_create_profile.assert_called_once_with(
        user_sub="u1", email="a@b.com", role="teacher"
    )


def test_handle_users_me_maps_http_error_to_json(monkeypatch, make_lambda_event) -> None:
    evt = make_lambda_event(method="GET", path="/users/me")
    monkeypatch.setattr(
        "services.auth.controller._claims_dict",
        lambda *a, **k: {"sub": "u1", "email": "a@b.com", "custom:role": "student"},
    )
    auth_svc = MagicMock()
    auth_svc.get_or_create_profile.side_effect = BadRequest("bad", code="X")

    resp = handle_users_me(
        evt,
        origin="https://app.example",
        auth_svc=auth_svc,
    )

    assert resp["statusCode"] == 400
    assert _body(resp) == {"message": "bad", "code": "X"}


def test_handle_users_me_returns_500_on_unhandled_exception(monkeypatch, make_lambda_event) -> None:
    evt = make_lambda_event(method="GET", path="/users/me")
    monkeypatch.setattr(
        "services.auth.controller._claims_dict",
        lambda *a, **k: {"sub": "u1", "email": "a@b.com", "custom:role": "student"},
    )
    auth_svc = MagicMock()
    auth_svc.get_or_create_profile.side_effect = RuntimeError("boom")

    resp = handle_users_me(
        evt,
        origin="*",
        auth_svc=auth_svc,
    )
    assert resp["statusCode"] == 500
    assert _body(resp)["code"] == "internal_error"


def test_handle_users_me_does_not_swallow_non_httperror_subclass(monkeypatch, make_lambda_event) -> None:
    """Pin behavior: only HttpError is mapped; other exceptions go to 500."""
    evt = make_lambda_event(method="GET", path="/users/me")
    monkeypatch.setattr(
        "services.auth.controller._claims_dict",
        lambda *a, **k: {"sub": "u1"},
    )

    class CustomErr(HttpError):
        pass

    auth_svc = MagicMock()
    auth_svc.get_or_create_profile.side_effect = CustomErr(418, "teapot", code="X")

    resp = handle_users_me(
        evt,
        origin="*",
        auth_svc=auth_svc,
    )
    assert resp["statusCode"] == 418
    assert _body(resp) == {"message": "teapot", "code": "X"}

