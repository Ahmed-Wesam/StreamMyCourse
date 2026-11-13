"""Runs registered user-deletion steps in ascending order."""

from __future__ import annotations

from services.user_deletion.errors import UserDeletionBlocked
from services.user_deletion.registry import UserDeletionRegistry


class UserDeletionService:
    def __init__(self, registry: UserDeletionRegistry) -> None:
        self._registry = registry

    def delete_user(self, user_sub: str) -> None:
        sub = (user_sub or "").strip()
        if not sub:
            raise ValueError("user_sub is required")
        for step in self._registry.ordered_steps():
            try:
                step.run(sub)
            except Exception as exc:
                if getattr(exc, "pgcode", None) == "23503":
                    raise UserDeletionBlocked(step.name, pgcode="23503") from exc
                raise
