"""HyperPay JOD amount formatting (fils minor units)."""

from __future__ import annotations

JOD_FILS_PER_MAJOR = 1000


def validate_whole_jod_fils(amount_minor: int) -> None:
    """Require amount in whole JOD (multiples of 1000 fils)."""
    if amount_minor % JOD_FILS_PER_MAJOR != 0:
        raise ValueError(
            f"amount_minor must be a whole JOD in fils (multiple of {JOD_FILS_PER_MAJOR})"
        )


def fils_to_hyperpay_amount(amount_minor: int) -> str:
    """Format fils minor units for HyperPay API (major units, two decimals)."""
    validate_whole_jod_fils(amount_minor)
    major = amount_minor // JOD_FILS_PER_MAJOR
    return f"{major}.00"
