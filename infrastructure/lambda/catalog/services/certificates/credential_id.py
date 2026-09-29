"""Credential ID helpers for certificates (RS-12)."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from typing import Callable

from services.certificates.models import CREDENTIAL_ID_RE

_HEX = "0123456789ABCDEF"


def normalize_credential_id(raw: str) -> str:
    return (raw or "").strip().upper()


def is_valid_credential_id(raw: str) -> bool:
    return bool(CREDENTIAL_ID_RE.match(normalize_credential_id(raw)))


def generate_credential_id(
    *,
    course_certificate_code: str,
    now: datetime,
    rng: Callable[[int], int],
) -> str:
    """Build ``RS-{6hex}-{UTC year}-{10hex}``; store uppercase."""
    code = (course_certificate_code or "").strip().upper()
    if len(code) != 6 or any(c not in _HEX for c in code):
        raise ValueError("course certificate_code must be 6 uppercase hex chars")
    utc_now = now.astimezone(timezone.utc) if now.tzinfo else now.replace(tzinfo=timezone.utc)
    suffix = "".join(_HEX[rng(16)] for _ in range(10))
    return f"RS-{code}-{utc_now.year}-{suffix}"


def format_issue_label(issue_date: date) -> str:
    """English month name + year, e.g. ``September 2026``."""
    return f"{calendar.month_name[issue_date.month]} {issue_date.year}"
