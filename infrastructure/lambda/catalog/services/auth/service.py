from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from services.auth.profile_allowlists import COUNTRIES, PROFESSIONS
from services.auth.ports import UserProfileRepositoryPort
from services.common.errors import BadRequest, NotFound


_MAX_GIVEN_NAME = 50
_MAX_FAMILY_NAME = 50
_MAX_INSTITUTION = 200
_MAX_RESEARCH_INTERESTS = 1000

_COUNTRY_SET = frozenset(COUNTRIES)
_PROFESSION_SET = frozenset(PROFESSIONS)


def _parse_iso_timestamp(key: str, raw: str) -> datetime:
    s = (raw or "").strip()
    if not s:
        raise BadRequest(f"'{key}' is required")
    normalized = s[:-1] + "+00:00" if s.endswith("Z") else s
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as e:
        raise BadRequest(f"'{key}' must be an ISO-8601 timestamp") from e


def _bounded_optional_str(body: Dict[str, Any], key: str, *, max_len: int) -> str:
    val = body.get(key)
    if val is None:
        return ""
    if not isinstance(val, str):
        raise BadRequest(f"'{key}' must be a string")
    text = val.strip()
    if len(text) > max_len:
        raise BadRequest(f"'{key}' must be at most {max_len} characters")
    return text


def _require_allowlist_value(body: Dict[str, Any], key: str, allowed: frozenset[str]) -> str:
    val = body.get(key)
    if not isinstance(val, str) or not val.strip():
        raise BadRequest(f"'{key}' is required")
    text = val.strip()
    if text not in allowed:
        raise BadRequest(f"'{key}' is not a supported value")
    return text


class UserProfileService:
    def __init__(self, repo: UserProfileRepositoryPort) -> None:
        self._repo = repo

    @staticmethod
    def _public_profile_body(
        *,
        user_sub: str,
        email: str,
        role: str,
        item: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "userId": user_sub,
            "email": email,
            "role": role,
            "cognitoSub": user_sub,
            "createdAt": str(item.get("createdAt", "") or ""),
            "updatedAt": str(item.get("updatedAt", "") or ""),
            "givenName": str(item.get("givenName", "") or ""),
            "familyName": str(item.get("familyName", "") or ""),
            "country": str(item.get("country", "") or ""),
            "profession": str(item.get("profession", "") or ""),
            "institution": str(item.get("institution", "") or ""),
            "researchInterests": str(item.get("researchInterests", "") or ""),
            "termsAcceptedAt": str(item.get("termsAcceptedAt", "") or ""),
            "privacyAcceptedAt": str(item.get("privacyAcceptedAt", "") or ""),
        }

    def get_or_create_profile(self, *, user_sub: str, email: str, role: str) -> Dict[str, Any]:
        sub = (user_sub or "").strip()
        if not sub:
            raise BadRequest("user_sub must not be empty")
        normalized_role = (role or "student").strip().lower()
        if normalized_role not in ("student", "teacher", "admin"):
            normalized_role = "student"
        item = self._repo.get_profile(sub)
        if item:
            raw_stored = str(item.get("role", "") or "").strip().lower()
            stored_role = (
                raw_stored if raw_stored in ("student", "teacher", "admin") else ""
            )
            prior = stored_role if stored_role else "student"
            effective_role = normalized_role
            resolved_email = str(item.get("email", "") or email or "").strip()
            if effective_role != prior:
                self._repo.put_profile(
                    user_sub=sub,
                    email=resolved_email or email or "",
                    role=effective_role,
                )
                item = self._repo.get_profile(sub) or item
            return self._public_profile_body(
                user_sub=sub,
                email=str(item.get("email", "") or email),
                role=effective_role,
                item=item,
            )
        self._repo.put_profile(user_sub=sub, email=email or "", role=normalized_role)
        created = self._repo.get_profile(sub)
        if not created:
            return self._public_profile_body(
                user_sub=sub,
                email=email,
                role=normalized_role,
                item={},
            )
        return self._public_profile_body(
            user_sub=sub,
            email=str(created.get("email", "") or email),
            role=str(created.get("role", "") or normalized_role),
            item=created,
        )

    def update_profile_fields(self, *, user_sub: str, body: Dict[str, Any]) -> Dict[str, Any]:
        sub = (user_sub or "").strip()
        if not sub:
            raise BadRequest("user_sub must not be empty")
        if not isinstance(body, dict):
            raise BadRequest("Request body must be a JSON object")

        country = _require_allowlist_value(body, "country", _COUNTRY_SET)
        profession = _require_allowlist_value(body, "profession", _PROFESSION_SET)
        given_name = _bounded_optional_str(body, "givenName", max_len=_MAX_GIVEN_NAME)
        family_name = _bounded_optional_str(body, "familyName", max_len=_MAX_FAMILY_NAME)
        institution = _bounded_optional_str(body, "institution", max_len=_MAX_INSTITUTION)
        research_interests = _bounded_optional_str(
            body, "researchInterests", max_len=_MAX_RESEARCH_INTERESTS
        )
        terms_raw = body.get("termsAcceptedAt")
        privacy_raw = body.get("privacyAcceptedAt")
        if not isinstance(terms_raw, str):
            raise BadRequest("'termsAcceptedAt' is required")
        if not isinstance(privacy_raw, str):
            raise BadRequest("'privacyAcceptedAt' is required")
        terms_accepted_at = _parse_iso_timestamp("termsAcceptedAt", terms_raw)
        privacy_accepted_at = _parse_iso_timestamp("privacyAcceptedAt", privacy_raw)

        if self._repo.get_profile(sub) is None:
            raise NotFound("User profile not found")

        updated = self._repo.update_profile_fields(
            user_sub=sub,
            given_name=given_name,
            family_name=family_name,
            country=country,
            profession=profession,
            institution=institution,
            research_interests=research_interests,
            terms_accepted_at=terms_accepted_at,
            privacy_accepted_at=privacy_accepted_at,
        )
        return self._public_profile_body(
            user_sub=sub,
            email=str(updated.get("email", "") or ""),
            role=str(updated.get("role", "") or "student"),
            item=updated,
        )
