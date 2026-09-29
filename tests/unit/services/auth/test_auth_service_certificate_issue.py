"""RS-12: profile name completion hooks certificate issuer (fakes only)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

import pytest

from services.auth.service import UserProfileService
from services.common.errors import BadRequest, NotFound

_TS = "2026-01-15T12:00:00Z"


class _FakeIssuer:
    def __init__(self, *, raise_on_issue: bool = False) -> None:
        self.calls: list[dict[str, str]] = []
        self.raise_on_issue = raise_on_issue

    def try_issue_for_user(self, *, user_sub: str, role: str) -> None:
        self.calls.append({"user_sub": user_sub, "role": role})
        if self.raise_on_issue:
            raise RuntimeError("issuer exploded")


class _FakeRepo:
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._item = initial

    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]:
        return self._item

    def put_profile(self, *, user_sub: str, email: str, role: str) -> Dict[str, Any]:
        raise NotImplementedError

    def get_student_active_session_id(self, user_sub: str) -> str:
        return ""

    def update_profile_fields(self, **kwargs: Any) -> Dict[str, Any]:
        assert self._item is not None
        self._item = {
            **self._item,
            "givenName": kwargs["given_name"],
            "familyName": kwargs["family_name"],
            "country": kwargs["country"],
            "profession": kwargs["profession"],
            "institution": kwargs["institution"],
            "researchInterests": kwargs["research_interests"],
            "termsAcceptedAt": kwargs["terms_accepted_at"].isoformat().replace("+00:00", "Z"),
            "privacyAcceptedAt": kwargs["privacy_accepted_at"]
            .isoformat()
            .replace("+00:00", "Z"),
            "updatedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        return dict(self._item)


def _base_profile() -> Dict[str, Any]:
    return {
        "userSub": "u1",
        "email": "ada@example.com",
        "role": "student",
        "cognitoSub": "u1",
        "createdAt": "t1",
        "updatedAt": "t2",
        "givenName": "",
        "familyName": "",
        "country": "",
        "profession": "",
        "institution": "",
        "researchInterests": "",
        "termsAcceptedAt": "",
        "privacyAcceptedAt": "",
    }


def _body(*, given: str = "Ada", family: str = "Lovelace") -> Dict[str, Any]:
    return {
        "givenName": given,
        "familyName": family,
        "country": "Jordan",
        "profession": "Physician",
        "institution": "Hospital",
        "researchInterests": "AI",
        "termsAcceptedAt": _TS,
        "privacyAcceptedAt": _TS,
    }


def test_profile_update_with_both_names_calls_issuer() -> None:
    repo = _FakeRepo(_base_profile())
    issuer = _FakeIssuer()
    svc = UserProfileService(repo, certificate_issuer=issuer)

    out = svc.update_profile_fields(user_sub="u1", body=_body())

    assert out["givenName"] == "Ada"
    assert out["familyName"] == "Lovelace"
    assert issuer.calls == [{"user_sub": "u1", "role": "student"}]


def test_profile_update_blank_family_name_does_not_call_issuer() -> None:
    repo = _FakeRepo(_base_profile())
    issuer = _FakeIssuer()
    svc = UserProfileService(repo, certificate_issuer=issuer)

    out = svc.update_profile_fields(user_sub="u1", body=_body(family=""))

    assert out["familyName"] == ""
    assert issuer.calls == []


def test_profile_update_blank_given_name_does_not_call_issuer() -> None:
    repo = _FakeRepo(_base_profile())
    issuer = _FakeIssuer()
    svc = UserProfileService(repo, certificate_issuer=issuer)

    out = svc.update_profile_fields(user_sub="u1", body=_body(given=""))

    assert out["givenName"] == ""
    assert issuer.calls == []


def test_raising_issuer_does_not_fail_profile_update() -> None:
    repo = _FakeRepo(_base_profile())
    issuer = _FakeIssuer(raise_on_issue=True)
    svc = UserProfileService(repo, certificate_issuer=issuer)

    out = svc.update_profile_fields(user_sub="u1", body=_body())

    assert out["givenName"] == "Ada"
    assert out["familyName"] == "Lovelace"
    assert len(issuer.calls) == 1


def test_profile_update_missing_profile_still_404() -> None:
    repo = _FakeRepo(None)
    issuer = _FakeIssuer()
    svc = UserProfileService(repo, certificate_issuer=issuer)

    with pytest.raises(NotFound):
        svc.update_profile_fields(user_sub="u1", body=_body())
    assert issuer.calls == []


def test_profile_update_bad_country_still_bad_request() -> None:
    repo = _FakeRepo(_base_profile())
    issuer = _FakeIssuer()
    svc = UserProfileService(repo, certificate_issuer=issuer)
    body = _body()
    body["country"] = "Atlantis"

    with pytest.raises(BadRequest):
        svc.update_profile_fields(user_sub="u1", body=body)
    assert issuer.calls == []
