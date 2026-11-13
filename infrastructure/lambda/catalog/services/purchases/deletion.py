"""Purchase deletion for operator user delete (DSQL-5 S4)."""

from __future__ import annotations

from typing import Protocol


class PurchaseDeletionRepo(Protocol):
    def delete_purchases_for_user(self, user_sub: str) -> int: ...


__all__ = ["PurchaseDeletionRepo"]
