"""Pure generator for ``courses.certificate_code`` (6 uppercase hex chars)."""

from __future__ import annotations

from typing import Callable

_HEX = "0123456789ABCDEF"
_MAX_ATTEMPTS = 20


def generate_certificate_code(
    *,
    rng: Callable[[int], int],
    taken: Callable[[str], bool] | None = None,
) -> str:
    """Return a 6-character uppercase hex code.

    ``rng(16)`` must return an int in ``0..15``. When ``taken`` is provided and
    returns True for a candidate, another code is generated (up to
    ``_MAX_ATTEMPTS``). Does not use the system clock.
    """
    for _ in range(_MAX_ATTEMPTS):
        code = "".join(_HEX[rng(16)] for _ in range(6))
        if taken is None or not taken(code):
            return code
    raise RuntimeError(
        f"exhausted {_MAX_ATTEMPTS} attempts generating unique certificate_code"
    )
