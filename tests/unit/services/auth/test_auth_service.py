from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from services.auth.service import UserProfileService


class _FakeRepo:
    def __init__(self, initial: Optional[Dict[str, Any]] = None) -> None:
        self._item = initial
        self.put_calls: list[Dict[str, str]] = []
        self.get_calls: list[str] = []

    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]:
        self.get_calls.append(user_sub)
        return self._item

    def put_profile(self, *, user_sub: str, email: str, role: str) -> Dict[str, Any]:
        self.put_calls.append({"user_sub": user_sub, "email": email, "role": role})
        # mirror the repo contract used by the service (camelCase keys).
        self._item = {
            "userSub": user_sub,
            "email": email,
            "role": role,
            "cognitoSub": user_sub,
            "createdAt": self._item.get("createdAt", "") if self._item else "",
            "updatedAt": self._item.get("updatedAt", "") if self._item else "",
        }
        return dict(self._item)


@pytest.mark.parametrize(
    "raw_role,expected",
    [
        (None, "student"),
        ("", "student"),
        (" student ", "student"),
        ("Teacher", "teacher"),
        ("ADMIN", "admin"),
        ("owner", "student"),  # invalid role coerced
    ],
)
def test_get_or_create_profile_normalizes_role_on_create(
    raw_role: str | None, expected: str
) -> None:
    repo = _FakeRepo(initial=None)
    svc = UserProfileService(repo)

    body = svc.get_or_create_profile(user_sub="u1", email="a@b.com", role=raw_role)  # type: ignore[arg-type]

    assert body["userId"] == "u1"
    assert body["email"] == "a@b.com"
    assert body["role"] == expected
    assert repo.put_calls[-1]["role"] == expected


def test_existing_profile_role_unchanged_does_not_write() -> None:
    repo = _FakeRepo(
        initial={
            "email": "stored@example.com",
            "role": "student",
            "createdAt": "t1",
            "updatedAt": "t2",
        }
    )
    svc = UserProfileService(repo)

    body = svc.get_or_create_profile(user_sub="u1", email="claims@example.com", role="student")

    assert body["email"] == "stored@example.com"
    assert body["role"] == "student"
    assert repo.put_calls == []
    assert repo.get_calls == ["u1"]


def test_existing_profile_role_promotion_writes_and_re_reads() -> None:
    repo = _FakeRepo(
        initial={
            "email": "stored@example.com",
            "role": "student",
            "createdAt": "t1",
            "updatedAt": "t2",
        }
    )
    svc = UserProfileService(repo)

    body = svc.get_or_create_profile(user_sub="u1", email="claims@example.com", role="teacher")

    assert body["role"] == "teacher"
    assert repo.put_calls == [
        {"user_sub": "u1", "email": "stored@example.com", "role": "teacher"}
    ]
    # initial read + read-after-write
    assert repo.get_calls == ["u1", "u1"]


def test_existing_profile_invalid_stored_role_defaults_to_student_prior() -> None:
    repo = _FakeRepo(
        initial={
            "email": "stored@example.com",
            "role": "poweruser",
            "createdAt": "t1",
            "updatedAt": "t2",
        }
    )
    svc = UserProfileService(repo)

    body = svc.get_or_create_profile(user_sub="u1", email="claims@example.com", role="teacher")

    assert body["role"] == "teacher"
    assert repo.put_calls[-1]["role"] == "teacher"


def test_create_profile_returns_fallback_when_second_read_is_none() -> None:
    class _RepoNoReadBack(_FakeRepo):
        def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]:
            self.get_calls.append(user_sub)
            # Return None even after put.
            return None

    repo = _RepoNoReadBack(initial=None)
    svc = UserProfileService(repo)

    body = svc.get_or_create_profile(user_sub="u1", email="a@b.com", role="student")

    assert body == {
        "userId": "u1",
        "email": "a@b.com",
        "role": "student",
        "cognitoSub": "u1",
        "createdAt": "",
        "updatedAt": "",
    }
