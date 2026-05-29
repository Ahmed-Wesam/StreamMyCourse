"""Build Kinescope playback watermark text from Cognito JWT claims."""

from __future__ import annotations

import re
from typing import Any

_MAX_WATERMARK_LENGTH = 120


def _claim_str(claims: dict[str, Any], key: str) -> str | None:
    value = claims.get(key)
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_name_part(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _name_line_from_claims(claims: dict[str, Any]) -> str | None:
    parts: list[str] = []
    for key in ("given_name", "family_name"):
        raw = _claim_str(claims, key)
        if raw is not None:
            parts.append(_normalize_name_part(raw))
    if parts:
        return " ".join(parts)
    return None


def missing_watermark_profile_fields(claims: dict[str, Any]) -> tuple[str, ...]:
    """Return missing profile fields: email, and name when both given_name and family_name are absent."""
    missing: list[str] = []
    if _name_line_from_claims(claims) is None:
        missing.append("name")
    if _claim_str(claims, "email") is None:
        missing.append("email")
    return tuple(missing)


def playback_watermark_from_claims(claims: dict[str, Any]) -> str | None:
    """Return a two-line watermark (name + email) when both are present."""
    if missing_watermark_profile_fields(claims):
        return None

    name_line = _name_line_from_claims(claims)
    email = _claim_str(claims, "email")
    assert name_line is not None and email is not None

    watermark = f"{name_line}\n{email}"

    if len(watermark) <= _MAX_WATERMARK_LENGTH:
        return watermark
    capped = _cap_watermark(watermark, _MAX_WATERMARK_LENGTH)
    if capped is None:
        return None
    return capped


def _cap_watermark(watermark: str, max_len: int) -> str | None:
    """Truncate while preserving a two-line name+email watermark when possible."""
    if len(watermark) <= max_len:
        return watermark
    if "\n" not in watermark:
        return watermark[:max_len]

    name_line, email_line = watermark.split("\n", 1)
    if not name_line.strip() or not email_line.strip():
        return None

    # Prefer full email; shorten the name line first.
    if len(email_line) + 1 < max_len:
        max_name_len = max_len - len(email_line) - 1
        trimmed_name = name_line[:max_name_len].rstrip()
        if trimmed_name:
            return f"{trimmed_name}\n{email_line}"
        return None

    # Email alone exceeds budget — truncate email but keep a non-empty name prefix.
    max_email_len = max_len - 2
    if max_email_len <= 0:
        return None
    name_budget = max_len - max_email_len - 1
    trimmed_name = name_line[:name_budget].rstrip() or name_line[:1]
    if not trimmed_name:
        return None
    return f"{trimmed_name}\n{email_line[:max_email_len]}"
