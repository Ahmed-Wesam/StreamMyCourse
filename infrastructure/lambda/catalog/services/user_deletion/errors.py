"""User deletion domain errors (not HTTP errors)."""

from __future__ import annotations


class UserDeletionBlocked(Exception):
    """A registered step hit a FK or other blocking constraint (SQLSTATE 23503)."""

    def __init__(self, step_name: str, *, pgcode: str = "23503") -> None:
        self.step_name = step_name
        self.pgcode = pgcode
        super().__init__(f"user deletion blocked at step {step_name!r} (pgcode={pgcode})")
