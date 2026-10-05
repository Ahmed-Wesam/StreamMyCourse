from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from services.auth.learning_preferences import RESEARCH_INTEREST_TAG_SET
from services.auth.ports import CertificateIssuerPort, UserProfileRepositoryPort
from services.auth.profile_allowlists import COUNTRIES, PROFESSIONS
from services.common.errors import BadRequest, NotFound


_MAX_GIVEN_NAME = 50
_MAX_FAMILY_NAME = 50
_MAX_INSTITUTION = 200
_MAX_RESEARCH_INTERESTS = 1000

_COUNTRY_SET = frozenset(COUNTRIES)
_PROFESSION_SET = frozenset(PROFESSIONS)
_PROFILE_BODY_KEYS = (
    "givenName",
    "familyName",
    "country",
    "profession",
    "institution",
    "researchInterests",
    "termsAcceptedAt",
    "privacyAcceptedAt",
)
_PREFERENCE_BODY_KEYS = (
    "autoplayNext",
    "autoMarkComplete",
    "progressCelebrations",
    "researchInterestTags",
)

logger = logging.getLogger(__name__)


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


def _pref_bool(item: Dict[str, Any], key: str) -> bool:
    value = item.get(key, True)
    if isinstance(value, bool):
        return value
    return True


def _pref_tags(item: Dict[str, Any]) -> list[str]:
    raw = item.get("researchInterestTags")
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(tag) for tag in raw if isinstance(tag, str)]


def _require_bool_field(body: Dict[str, Any], key: str, current: bool) -> bool:
    if key not in body:
        return current
    value = body.get(key)
    if not isinstance(value, bool):
        raise BadRequest(f"'{key}' must be a boolean")
    return value


def _parse_research_interest_tags(body: Dict[str, Any], current: list[str]) -> list[str]:
    if "researchInterestTags" not in body:
        return list(current)
    raw = body.get("researchInterestTags")
    if not isinstance(raw, list) or any(not isinstance(item, str) for item in raw):
        raise BadRequest("researchInterestTags must be a list of known keys")
    unknown = [item for item in raw if item not in RESEARCH_INTEREST_TAG_SET]
    if unknown:
        raise BadRequest("researchInterestTags contains an unsupported value")
    tags: list[str] = []
    for item in raw:
        if item not in tags:
            tags.append(item)
    return tags


def _require_allowlist_value(body: Dict[str, Any], key: str, allowed: frozenset[str]) -> str:
    val = body.get(key)
    if not isinstance(val, str) or not val.strip():
        raise BadRequest(f"'{key}' is required")
    text = val.strip()
    if text not in allowed:
        raise BadRequest(f"'{key}' is not a supported value")
    return text


class UserProfileService:
    def __init__(
        self,
        repo: UserProfileRepositoryPort,
        certificate_issuer: CertificateIssuerPort | None = None,
    ) -> None:
        self._repo = repo
        self._certificate_issuer = certificate_issuer

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
            "autoplayNext": _pref_bool(item, "autoplayNext"),
            "autoMarkComplete": _pref_bool(item, "autoMarkComplete"),
            "progressCelebrations": _pref_bool(item, "progressCelebrations"),
            "researchInterestTags": _pref_tags(item),
            "lastLoginAt": str(item.get("lastLoginAt", "") or ""),
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

    def _profile_response(self, *, user_sub: str, item: Dict[str, Any]) -> Dict[str, Any]:
        return self._public_profile_body(
            user_sub=user_sub,
            email=str(item.get("email", "") or ""),
            role=str(item.get("role", "") or "student"),
            item=item,
        )

    def _apply_learning_preferences(self, *, user_sub: str, body: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        updated = self._repo.update_learning_preferences(
            user_sub=user_sub,
            autoplay_next=_require_bool_field(body, "autoplayNext", _pref_bool(current, "autoplayNext")),
            auto_mark_complete=_require_bool_field(
                body, "autoMarkComplete", _pref_bool(current, "autoMarkComplete")
            ),
            progress_celebrations=_require_bool_field(
                body, "progressCelebrations", _pref_bool(current, "progressCelebrations")
            ),
            research_interest_tags=_parse_research_interest_tags(body, _pref_tags(current)),
        )
        return self._profile_response(user_sub=user_sub, item=updated)

    def update_profile_fields(self, *, user_sub: str, body: Dict[str, Any]) -> Dict[str, Any]:
        sub = (user_sub or "").strip()
        if not sub:
            raise BadRequest("user_sub must not be empty")
        if not isinstance(body, dict):
            raise BadRequest("Request body must be a JSON object")

        if "resetPreferences" in body:
            reset_flag = body.get("resetPreferences")
            if not isinstance(reset_flag, bool):
                raise BadRequest("'resetPreferences' must be a boolean")
            if reset_flag:
                if self._repo.get_profile(sub) is None:
                    raise NotFound("User profile not found")
                updated = self._repo.reset_built_preferences(user_sub=sub)
                return self._profile_response(user_sub=sub, item=updated)

        has_profile = any(key in body for key in _PROFILE_BODY_KEYS)
        has_preferences = any(key in body for key in _PREFERENCE_BODY_KEYS)
        if has_preferences and not has_profile:
            current = self._repo.get_profile(sub)
            if current is None:
                raise NotFound("User profile not found")
            return self._apply_learning_preferences(user_sub=sub, body=body, current=current)

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
        response = self._public_profile_body(
            user_sub=sub,
            email=str(updated.get("email", "") or ""),
            role=str(updated.get("role", "") or "student"),
            item=updated,
        )
        if given_name and family_name and self._certificate_issuer is not None:
            try:
                self._certificate_issuer.try_issue_for_user(
                    user_sub=sub,
                    role=str(response.get("role", "") or "student"),
                )
            except Exception:
                logger.exception(
                    "Certificate issue after profile name completion failed",
                    extra={"user_sub": sub},
                )
        if has_preferences:
            return self._apply_learning_preferences(user_sub=sub, body=body, current=updated)
        return response
