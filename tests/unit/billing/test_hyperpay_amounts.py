"""HyperPay JOD amount formatting and validation (domain.amounts)."""

from __future__ import annotations

import pytest

from domain.amounts import (
    JOD_FILS_PER_MAJOR,
    fils_to_hyperpay_amount,
    validate_whole_jod_fils,
)


def test_jod_fils_constant() -> None:
    assert JOD_FILS_PER_MAJOR == 1000


@pytest.mark.parametrize(
    ("amount_minor", "expected"),
    [
        (50_000, "50.00"),
        (150_000, "150.00"),
        (1000, "1.00"),
        (0, "0.00"),
    ],
)
def test_fils_to_hyperpay_amount(amount_minor: int, expected: str) -> None:
    assert fils_to_hyperpay_amount(amount_minor) == expected


@pytest.mark.parametrize("amount_minor", [500, 1500, 50_500, 99_999])
def test_validate_rejects_non_whole_jod_fils(amount_minor: int) -> None:
    with pytest.raises(ValueError):
        validate_whole_jod_fils(amount_minor)


@pytest.mark.parametrize("amount_minor", [0, 1000, 50_000, 150_000])
def test_validate_accepts_whole_jod_fils(amount_minor: int) -> None:
    validate_whole_jod_fils(amount_minor)
