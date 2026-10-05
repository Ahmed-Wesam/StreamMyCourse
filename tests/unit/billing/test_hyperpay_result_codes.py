"""HyperPay result-code classification (domain.result_codes)."""

from __future__ import annotations

import pytest

from domain.result_codes import classify_result_code


@pytest.mark.parametrize(
    "code",
    [
        "000.000.000",
        "000.000.100",
        "000.100.110",
        "000.100.123",
        "000.300.000",
        "000.600.000",
        "000.400.110",
        "000.400.120",
    ],
)
def test_success_codes(code: str) -> None:
    assert classify_result_code(code) == "success"


@pytest.mark.parametrize(
    "code",
    [
        "000.200.000",
        "000.200.100",
        "000.200",
    ],
)
def test_pending_000_200_is_not_success(code: str) -> None:
    assert classify_result_code(code) == "pending"
    assert classify_result_code(code) != "success"


def test_pending_is_not_failed() -> None:
    assert classify_result_code("000.200.000") != "failed"


@pytest.mark.parametrize(
    "code",
    [
        "800.100.153",
        "100.380.401",
        "000.100.200",
        "000.400.100",
        "000.400.130",
        "000.500.000",
        "",
        "invalid",
    ],
)
def test_decline_and_other_codes_are_failed(code: str) -> None:
    assert classify_result_code(code) == "failed"
