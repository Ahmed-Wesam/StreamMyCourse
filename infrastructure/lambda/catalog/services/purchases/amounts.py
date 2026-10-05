"""JOD list-price validation (fils minor units, 1000 fils = 1 JOD)."""

from __future__ import annotations

JOD_FILS_PER_MAJOR = 1000
DEFAULT_PURCHASE_CURRENCY = "JOD"


def validate_whole_jod_fils(amount_minor: int) -> None:
    """Require amount in whole JOD (multiples of 1000 fils)."""
    if amount_minor % JOD_FILS_PER_MAJOR != 0:
        raise ValueError(
            f"amount_minor must be a whole JOD in fils (multiple of {JOD_FILS_PER_MAJOR})"
        )
