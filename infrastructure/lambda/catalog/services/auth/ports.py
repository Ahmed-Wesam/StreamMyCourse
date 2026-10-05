"""Ports for the auth bounded context.

``UserProfileService`` depends on :class:`UserProfileRepositoryPort` rather than
a concrete repository class so the bootstrap can inject either the DynamoDB
adapter (``repo.UserProfileRepository``) or the PostgreSQL adapter
(``rds_repo.UserProfileRdsRepository``) without service-layer changes.

Dict shape contract (returned by both adapters):
    {
        "email":      str,          # present, may be empty
        "role":       str,          # "student" | "teacher" | "admin"
        "cognitoSub": str,          # usually equal to the user_sub key
        "createdAt":  str,          # ISO-8601 UTC
        "updatedAt":  str,          # ISO-8601 UTC
        "userSub":    str,          # Cognito sub, same as the key
    }

Keys are **camelCase** regardless of the underlying store because the service
layer and public API contract already assume camelCase.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Protocol


class UserProfileRepositoryPort(Protocol):
    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]: ...

    def get_student_active_session_id(self, user_sub: str) -> str: ...

    def put_profile(
        self, *, user_sub: str, email: str, role: str
    ) -> Dict[str, Any]: ...

    def update_profile_fields(
        self,
        *,
        user_sub: str,
        given_name: str,
        family_name: str,
        country: str,
        profession: str,
        institution: str,
        research_interests: str,
        terms_accepted_at: datetime,
        privacy_accepted_at: datetime,
    ) -> Dict[str, Any]: ...

    def update_learning_preferences(
        self,
        *,
        user_sub: str,
        autoplay_next: bool,
        auto_mark_complete: bool,
        progress_celebrations: bool,
        research_interest_tags: list[str],
    ) -> Dict[str, Any]: ...

    def reset_built_preferences(self, *, user_sub: str) -> Dict[str, Any]: ...


class CertificateIssuerPort(Protocol):
    """Optional RS-12 hook; duck-typed to CertificatesService.try_issue_for_user."""

    def try_issue_for_user(self, *, user_sub: str, role: str) -> None: ...
