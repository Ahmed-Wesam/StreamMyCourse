"""RS-6 Slice A: PATCH /users/me profile validation and controller wiring."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from services.auth.controller import handle_users_me_patch
from services.auth.service import UserProfileService
from services.common.errors import BadRequest


def _body(resp: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(resp["body"])


def _valid_patch_body(**overrides: Any) -> Dict[str, Any]:
    base = {
        "givenName": "Ada",
        "familyName": "Lovelace",
        "country": "Jordan",
        "profession": "Researcher",
        "institution": "RS Institute",
        "researchInterests": "Statistics",
        "termsAcceptedAt": "2026-01-15T10:00:00Z",
        "privacyAcceptedAt": "2026-01-15T10:00:00Z",
    }
    base.update(overrides)
    return base


class _TrackingRepo:
    def __init__(self, profile: Optional[Dict[str, Any]] = None) -> None:
        self._profile = profile
        self.update_calls: List[Dict[str, Any]] = []

    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]:
        return self._profile

    def put_profile(self, *, user_sub: str, email: str, role: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_student_active_session_id(self, user_sub: str) -> str:
        return ""

    def update_profile_fields(self, **kwargs: Any) -> Dict[str, Any]:  # noqa: ANN401
        self.update_calls.append(dict(kwargs))
        merged = dict(self._profile or {})
        merged.update(
            {
                "givenName": kwargs.get("given_name", ""),
                "familyName": kwargs.get("family_name", ""),
                "country": kwargs.get("country", ""),
                "profession": kwargs.get("profession", ""),
            }
        )
        self._profile = merged
        return merged


class TestUpdateProfileFieldsService:
    def test_unknown_country_returns_400_no_db_write(self) -> None:
        repo = _TrackingRepo(
            profile={
                "userSub": "u1",
                "email": "a@b.com",
                "role": "student",
                "cognitoSub": "u1",
                "createdAt": "t1",
                "updatedAt": "t2",
            }
        )
        svc = UserProfileService(repo)
        with pytest.raises(BadRequest):
            svc.update_profile_fields(
                user_sub="u1",
                body=_valid_patch_body(country="Narnia"),
            )
        assert repo.update_calls == []

    def test_patch_ignores_role_email_user_sub_in_body(self) -> None:
        repo = _TrackingRepo(
            profile={
                "userSub": "token-sub",
                "email": "stored@example.com",
                "role": "student",
                "cognitoSub": "token-sub",
                "createdAt": "t1",
                "updatedAt": "t2",
                "givenName": "Ada",
                "familyName": "Lovelace",
                "country": "Jordan",
                "profession": "Researcher",
                "institution": "RS Institute",
                "researchInterests": "Statistics",
                "termsAcceptedAt": "2026-01-15T10:00:00+00:00",
                "privacyAcceptedAt": "2026-01-15T10:00:00+00:00",
            }
        )
        svc = UserProfileService(repo)
        svc.update_profile_fields(
            user_sub="token-sub",
            body=_valid_patch_body(
                role="admin",
                email="attacker@evil.com",
                userSub="other-sub",
            ),
        )
        assert repo.update_calls
        assert repo.update_calls[0]["user_sub"] == "token-sub"
        assert "email" not in repo.update_calls[0]
        assert "role" not in repo.update_calls[0]

    @pytest.mark.parametrize(
        "field,key,max_len",
        [
            ("givenName", "givenName", 50),
            ("familyName", "familyName", 50),
            ("institution", "institution", 200),
            ("researchInterests", "researchInterests", 1000),
        ],
    )
    def test_rejects_oversize_profile_strings(
        self, field: str, key: str, max_len: int
    ) -> None:
        repo = _TrackingRepo(profile={"userSub": "u1", "email": "a@b.com", "role": "student"})
        svc = UserProfileService(repo)
        with pytest.raises(BadRequest):
            svc.update_profile_fields(
                user_sub="u1",
                body=_valid_patch_body(**{key: "x" * (max_len + 1)}),
            )
        assert repo.update_calls == []


def test_handle_users_me_patch_uses_token_sub_only(
    make_lambda_event,
) -> None:
    evt = make_lambda_event(
        method="PATCH",
        path="/users/me",
        body=_valid_patch_body(userSub="evil", email="x@y.com", role="admin"),
    )
    evt["requestContext"]["authorizer"] = {
        "claims": {"sub": "real-sub", "email": "real@example.com", "custom:role": "student"}
    }
    auth_svc = MagicMock()
    auth_svc.update_profile_fields.return_value = {"userId": "real-sub"}

    resp = handle_users_me_patch(evt, origin="*", auth_svc=auth_svc)

    assert resp["statusCode"] == 200
    auth_svc.get_or_create_profile.assert_called_once_with(
        user_sub="real-sub", email="real@example.com", role="student"
    )
    auth_svc.update_profile_fields.assert_called_once()
    call_kw = auth_svc.update_profile_fields.call_args.kwargs
    assert call_kw["user_sub"] == "real-sub"
