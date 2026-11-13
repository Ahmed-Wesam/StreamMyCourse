"""Identity-scoped deletion steps (DSQL-2: users row only)."""

from __future__ import annotations

from typing import Protocol

from services.user_deletion.registry import UserDeletionRegistry

_USERS_STEP_ORDER = 1000


class UserRowDeleter(Protocol):
    def delete_user_row(self, user_sub: str) -> int:
        """Delete the ``users`` row; return rowcount."""


def register_identity_steps(registry: UserDeletionRegistry, deleter: UserRowDeleter) -> None:
    registry.register(
        name="users",
        order=_USERS_STEP_ORDER,
        run=lambda user_sub: deleter.delete_user_row(user_sub),
    )
