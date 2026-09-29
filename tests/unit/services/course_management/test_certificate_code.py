"""RS-12: pure course certificate_code generator."""

from __future__ import annotations

import pytest

from services.course_management.certificate_code import generate_certificate_code


def test_generate_certificate_code_is_six_uppercase_hex() -> None:
    # Fixed sequence: 0..15 then wraps; first six nibbles -> "012345"
    n = {"i": 0}

    def rng(bound: int) -> int:
        assert bound == 16
        v = n["i"] % 16
        n["i"] += 1
        return v

    code = generate_certificate_code(rng=rng)
    assert code == "012345"
    assert len(code) == 6
    assert all(c in "0123456789ABCDEF" for c in code)


def test_generate_certificate_code_retries_when_taken() -> None:
    # First code "AAAAAA" taken; second "BBBBBB" free.
    calls = {"n": 0}
    taken_seen: list[str] = []

    def rng(bound: int) -> int:
        assert bound == 16
        calls["n"] += 1
        # First 6 calls -> A (10); next 6 -> B (11)
        return 10 if calls["n"] <= 6 else 11

    def taken(code: str) -> bool:
        taken_seen.append(code)
        return code == "AAAAAA"

    code = generate_certificate_code(rng=rng, taken=taken)
    assert code == "BBBBBB"
    assert taken_seen == ["AAAAAA", "BBBBBB"]


def test_generate_certificate_code_raises_after_retry_cap() -> None:
    def rng(bound: int) -> int:
        assert bound == 16
        return 0

    def taken(_code: str) -> bool:
        return True

    with pytest.raises(RuntimeError, match="certificate_code"):
        generate_certificate_code(rng=rng, taken=taken)
