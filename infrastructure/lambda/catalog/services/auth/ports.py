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

from typing import Any, Dict, Optional, Protocol


class UserProfileRepositoryPort(Protocol):
    def get_profile(self, user_sub: str) -> Optional[Dict[str, Any]]: ...

    def put_profile(
        self, *, user_sub: str, email: str, role: str
    ) -> Dict[str, Any]: ...
