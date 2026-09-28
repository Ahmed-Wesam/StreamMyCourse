from __future__ import annotations

import re
from typing import Any, Dict, Mapping

from services.common.errors import BadRequest
from services.contact.models import ContactSubmission

CONTACT_CATEGORIES: tuple[str, ...] = (
    "General Question",
    "Course Support",
    "Assignment Support",
    "Certificate Support",
    "Research Team",
    "Technical Issue",
    "Billing Question",
    "Partnership Inquiry",
)

CONTACT_ALLOWED_KEYS = frozenset(
    {"name", "email", "category", "subject", "message", "rs_hp"}
)

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _reject_unknown_keys(body: Mapping[str, Any]) -> None:
    unknown = set(body.keys()) - CONTACT_ALLOWED_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise BadRequest(f"Unknown field(s): {names}")


def _require_non_empty_str(body: Dict[str, Any], key: str) -> str:
    val = body.get(key)
    if not isinstance(val, str) or not val.strip():
        raise BadRequest(f"'{key}' is required")
    return val.strip()


def _reject_comma_or_crlf(value: str, field: str) -> None:
    if any(ch in value for ch in (",", "\n", "\r")):
        raise BadRequest(f"'{field}' must not contain commas or line breaks")


def _validate_email_shape(email: str) -> None:
    if len(email) > 254:
        raise BadRequest("'email' is too long")
    if not _EMAIL_RE.match(email):
        raise BadRequest("'email' is not a valid email address")


def parse_contact_payload(body: Dict[str, Any]) -> ContactSubmission:
    if not isinstance(body, dict):
        raise BadRequest("Request body must be a JSON object")
    _reject_unknown_keys(body)

    name = _require_non_empty_str(body, "name")
    email = _require_non_empty_str(body, "email")
    category = _require_non_empty_str(body, "category")
    subject = _require_non_empty_str(body, "subject")
    message = _require_non_empty_str(body, "message")

    rs_hp_raw = body.get("rs_hp", "")
    if rs_hp_raw is None or rs_hp_raw == "":
        honeypot = ""
    elif isinstance(rs_hp_raw, str):
        honeypot = rs_hp_raw.strip()
    else:
        # JSON clients that send non-string rs_hp are treated as bots (same as filled honeypot).
        honeypot = "non-string"

    if len(name) > 100:
        raise BadRequest("'name' is too long")
    if len(subject) > 200:
        raise BadRequest("'subject' is too long")
    if len(message) > 5000:
        raise BadRequest("'message' is too long")

    _reject_comma_or_crlf(name, "name")
    _reject_comma_or_crlf(email, "email")
    _reject_comma_or_crlf(subject, "subject")
    _validate_email_shape(email)

    if category not in CONTACT_CATEGORIES:
        raise BadRequest("'category' is not valid")

    return ContactSubmission(
        name=name,
        email=email,
        category=category,
        subject=subject,
        message=message,
        honeypot=honeypot,
    )
