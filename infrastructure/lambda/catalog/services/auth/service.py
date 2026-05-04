from __future__ import annotations

from typing import Any, Dict

from services.auth.ports import UserProfileRepositoryPort


class UserProfileService:
    def __init__(self, repo: UserProfileRepositoryPort) -> None:
        self._repo = repo

    def get_or_create_profile(self, *, user_sub: str, email: str, role: str) -> Dict[str, Any]:
        normalized_role = (role or "student").strip().lower()
        if normalized_role not in ("student", "teacher", "admin"):
            normalized_role = "student"
        item = self._repo.get_profile(user_sub)
        if item:
            raw_stored = str(item.get("role", "") or "").strip().lower()
            stored_role = (
                raw_stored if raw_stored in ("student", "teacher", "admin") else ""
            )
            prior = stored_role if stored_role else "student"
            # Cognito (JWT) is authoritative; Dynamo may still say student after custom:role promotion.
            effective_role = normalized_role
            resolved_email = str(item.get("email", "") or email or "").strip()
            if effective_role != prior:
                self._repo.put_profile(
                    user_sub=user_sub,
                    email=resolved_email or email or "",
                    role=effective_role,
                )
                item = self._repo.get_profile(user_sub) or item
            return {
                "userId": user_sub,
                "email": str(item.get("email", "") or email),
                "role": effective_role,
                "cognitoSub": user_sub,
                "createdAt": str(item.get("createdAt", "") or ""),
                "updatedAt": str(item.get("updatedAt", "") or ""),
            }
        self._repo.put_profile(user_sub=user_sub, email=email or "", role=normalized_role)
        created = self._repo.get_profile(user_sub)
        if not created:
            return {
                "userId": user_sub,
                "email": email,
                "role": normalized_role,
                "cognitoSub": user_sub,
                "createdAt": "",
                "updatedAt": "",
            }
        return {
            "userId": user_sub,
            "email": str(created.get("email", "") or email),
            "role": str(created.get("role", "") or normalized_role),
            "cognitoSub": user_sub,
            "createdAt": str(created.get("createdAt", "") or ""),
            "updatedAt": str(created.get("updatedAt", "") or ""),
        }
