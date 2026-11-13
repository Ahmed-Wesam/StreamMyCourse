"""Valid PATCH /users/me bodies for integration tests."""

from __future__ import annotations

from typing import Any

_TERMS_AT = "2025-01-01T00:00:00.000Z"
_PRIVACY_AT = "2025-01-01T00:00:00.000Z"


def valid_profile_patch_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "givenName": "RS",
        "familyName": "Integration",
        "country": "Jordan",
        "profession": "Researcher",
        "institution": "RS Institute",
        "researchInterests": "Statistics",
        "termsAcceptedAt": _TERMS_AT,
        "privacyAcceptedAt": _PRIVACY_AT,
    }
    body.update(overrides)
    return body
