from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Protocol

from services.common.errors import ServiceUnavailable
from services.contact.models import ContactSubmission
from services.contact.validation import parse_contact_payload

logger = logging.getLogger(__name__)

SUPPORT_INBOX = "support@researchspectrum.org"

EnqueueFn = Callable[[str, Dict[str, Any]], None]


class _EnqueuePort(Protocol):
    def __call__(self, queue_url: str, payload: Dict[str, Any]) -> None: ...


def _format_body_text(submission: ContactSubmission) -> str:
    return (
        "Research Spectrum contact form submission\n\n"
        f"Name: {submission.name}\n"
        f"Email: {submission.email}\n"
        f"Category: {submission.category}\n"
        f"Subject: {submission.subject}\n\n"
        "Message:\n"
        f"{submission.message}\n"
    )


def _sqs_payload(submission: ContactSubmission) -> Dict[str, Any]:
    return {
        "to": SUPPORT_INBOX,
        "subject": f"[Research Spectrum] {submission.category}: {submission.subject}",
        "bodyText": _format_body_text(submission),
        "replyTo": submission.email,
    }


class ContactService:
    def __init__(
        self,
        *,
        queue_url: str,
        enqueue: EnqueueFn,
    ) -> None:
        self._queue_url = (queue_url or "").strip()
        self._enqueue = enqueue

    def submit_from_dict(self, body: Dict[str, Any]) -> None:
        submission = parse_contact_payload(body)
        self.submit(submission)

    def submit(self, submission: ContactSubmission) -> None:
        if submission.honeypot:
            logger.info("Contact honeypot triggered; skipping enqueue")
            return
        if not self._queue_url:
            raise ServiceUnavailable(
                "Contact messaging is not configured (TRANSACTIONAL_MAIL_QUEUE_URL is empty)"
            )
        payload = _sqs_payload(submission)
        try:
            self._enqueue(self._queue_url, payload)
        except ServiceUnavailable:
            raise
        except Exception as exc:
            logger.exception("Failed to enqueue contact form message")
            raise ServiceUnavailable("Contact messaging is temporarily unavailable") from exc
