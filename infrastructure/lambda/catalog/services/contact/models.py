from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContactSubmission:
    name: str
    email: str
    category: str
    subject: str
    message: str
    honeypot: str = ""
