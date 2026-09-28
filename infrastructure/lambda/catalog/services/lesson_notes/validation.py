"""Validate lesson note body and optional playback timestamp."""

from __future__ import annotations

import re

from services.common.errors import BadRequest
from services.lesson_notes.models import MAX_NOTE_BODY_LEN, MAX_TIMESTAMP_SEC, MIN_NOTE_BODY_LEN

_TAG_LIKE = re.compile(r"<[a-zA-Z/!]")


def validate_note_body(body: str) -> str:
    """Return trimmed body after length and markup checks."""
    if not isinstance(body, str):
        raise BadRequest("body must be a string")
    trimmed = body.strip()
    if len(trimmed) < MIN_NOTE_BODY_LEN:
        raise BadRequest("body must be between 1 and 4000 characters", code="invalid_body")
    if len(trimmed) > MAX_NOTE_BODY_LEN:
        raise BadRequest("body must be between 1 and 4000 characters", code="invalid_body")
    if _TAG_LIKE.search(trimmed):
        raise BadRequest("Invalid markup in body", code="invalid_markup")
    return trimmed


def validate_timestamp_sec(value: int | None) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise BadRequest("timestampSec must be an integer", code="invalid_timestamp")
    if value < 0 or value > MAX_TIMESTAMP_SEC:
        raise BadRequest(
            f"timestampSec must be between 0 and {MAX_TIMESTAMP_SEC}",
            code="invalid_timestamp",
        )
    return value
