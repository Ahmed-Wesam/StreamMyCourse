"""HyperPay payment result code classification."""

from __future__ import annotations

import re
from typing import Literal

ResultClassification = Literal["success", "pending", "failed"]

_SUCCESS_PATTERN = re.compile(
    r"^(000\.000\.|000\.100\.1|000\.[36]|000\.400\.[1][12]0)"
)
_PENDING_PREFIX = "000.200"


def classify_result_code(code: str) -> ResultClassification:
    """Map a HyperPay ``result.code`` to success, pending, or failed."""
    normalized = (code or "").strip()
    if normalized.startswith(_PENDING_PREFIX):
        return "pending"
    if _SUCCESS_PATTERN.match(normalized):
        return "success"
    return "failed"
