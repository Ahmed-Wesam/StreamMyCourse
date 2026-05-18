"""Subscription period bounds from PayTabs IPN (v1 monthly)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

# v1 billing interval is monthly only (WS1).
_MONTHLY_PERIOD_DAYS = 30


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def ensure_grant_period_bounds(
    payload: dict[str, Any],
    period_start: str | None,
    period_end: str | None,
) -> tuple[str | None, str | None]:
    """Ensure granting events have period_end (derive from transaction_time when absent)."""
    if period_end:
        return period_start, period_end

    anchor = _parse_timestamp(
        payload.get("transaction_time")
        or payload.get("tran_time")
        or payload.get("payment_date")
    )
    if anchor is None:
        return period_start, period_end

    end_dt = anchor + timedelta(days=_MONTHLY_PERIOD_DAYS)
    start_out = period_start if period_start else anchor.isoformat()
    return start_out, end_dt.isoformat()
