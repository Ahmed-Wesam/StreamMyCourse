"""RS-16: learning preferences and last login on /users/me."""

from __future__ import annotations

from typing import Any

import pytest

from services.auth.service import UserProfileService
from services.common.errors import BadRequest

_PROFILE = {
    "userSub": "u1",
    "email": "a@b.com",
    "role": "student",
    "cognitoSub": "u1",
    "createdAt": "2026-01-01T00:00:00+00:00",
    "updatedAt": "2026-02-01T00:00:00+00:00",
    "givenName": "Ada",
    "familyName": "Lovelace",
    "country": "Jordan",
    "profession": "Researcher",
    "institution": "RS Institute",
    "researchInterests": "Keep this free text",
    "termsAcceptedAt": "2026-01-15T10:00:00+00:00",
    "privacyAcceptedAt": "2026-01-15T10:00:00+00:00",
    "autoplayNext": True,
    "autoMarkComplete": True,
    "progressCelebrations": True,
    "researchInterestTags": ["systematic_reviews"],
    "lastLoginAt": "2026-10-01T08:00:00+00:00",
}


class _PrefRepo:
    def __init__(self) -> None:
        self.profile = dict(_PROFILE)
        self.pref_calls: list[dict[str, Any]] = []
        self.reset_calls: list[str] = []

    def get_profile(self, user_sub: str) -> dict[str, Any] | None:
        return dict(self.profile) if user_sub == "u1" else None

    def put_profile(self, *, user_sub: str, email: str, role: str) -> dict[str, Any]:
        raise AssertionError("put_profile should not run")

    def get_student_active_session_id(self, user_sub: str) -> str:
        return ""

    def update_profile_fields(self, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("profile columns should stay untouched")

    def update_learning_preferences(self, **kwargs: Any) -> dict[str, Any]:
        self.pref_calls.append(dict(kwargs))
        self.profile["autoplayNext"] = kwargs["autoplay_next"]
        self.profile["autoMarkComplete"] = kwargs["auto_mark_complete"]
        self.profile["progressCelebrations"] = kwargs["progress_celebrations"]
        self.profile["researchInterestTags"] = list(kwargs["research_interest_tags"])
        return dict(self.profile)

    def reset_built_preferences(self, *, user_sub: str) -> dict[str, Any]:
        self.reset_calls.append(user_sub)
        self.profile["autoplayNext"] = True
        self.profile["autoMarkComplete"] = True
        self.profile["progressCelebrations"] = True
        self.profile["researchInterestTags"] = ["systematic_reviews", "meta_analysis"]
        return dict(self.profile)


def test_get_profile_returns_preferences_created_at_and_last_login() -> None:
    svc = UserProfileService(_PrefRepo())
    body = svc.get_or_create_profile(user_sub="u1", email="a@b.com", role="student")
    assert body["createdAt"] == "2026-01-01T00:00:00+00:00"
    assert body["lastLoginAt"] == "2026-10-01T08:00:00+00:00"
    assert body["autoplayNext"] is True
    assert body["autoMarkComplete"] is True
    assert body["progressCelebrations"] is True
    assert body["researchInterestTags"] == ["systematic_reviews"]
    assert body["researchInterests"] == "Keep this free text"


def test_patch_preferences_without_profile_fields() -> None:
    repo = _PrefRepo()
    svc = UserProfileService(repo)
    body = svc.update_profile_fields(
        user_sub="u1",
        body={
            "autoplayNext": False,
            "autoMarkComplete": True,
            "progressCelebrations": False,
            "researchInterestTags": ["surgical_research", "database_research"],
        },
    )
    assert repo.pref_calls[0]["autoplay_next"] is False
    assert repo.pref_calls[0]["auto_mark_complete"] is True
    assert repo.pref_calls[0]["progress_celebrations"] is False
    assert repo.pref_calls[0]["research_interest_tags"] == [
        "surgical_research",
        "database_research",
    ]
    assert body["researchInterests"] == "Keep this free text"
    assert repo.reset_calls == []


def test_research_interest_tags_reject_free_text() -> None:
    svc = UserProfileService(_PrefRepo())
    with pytest.raises(BadRequest, match="researchInterestTags"):
        svc.update_profile_fields(
            user_sub="u1",
            body={"researchInterestTags": ["brand new interest"]},
        )


def test_reset_built_preferences_only() -> None:
    repo = _PrefRepo()
    svc = UserProfileService(repo)
    body = svc.update_profile_fields(user_sub="u1", body={"resetPreferences": True})
    assert repo.reset_calls == ["u1"]
    assert repo.pref_calls == []
    assert body["autoplayNext"] is True
    assert body["autoMarkComplete"] is True
    assert body["progressCelebrations"] is True
    assert body["researchInterestTags"] == ["systematic_reviews", "meta_analysis"]
    assert body["researchInterests"] == "Keep this free text"
    assert body["givenName"] == "Ada"
