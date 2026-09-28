"""Unit tests for contact submission service (enqueue + honeypot)."""

from __future__ import annotations

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from services.common.errors import BadRequest, ServiceUnavailable
from services.contact.models import ContactSubmission
from services.contact.service import ContactService, SUPPORT_INBOX


@pytest.fixture
def sent_messages() -> List[Dict[str, Any]]:
    return []


@pytest.fixture
def contact_svc(sent_messages: List[Dict[str, Any]]) -> ContactService:
    def _enqueue(queue_url: str, payload: Dict[str, Any]) -> None:
        assert queue_url == "https://sqs.example/queue"
        sent_messages.append(payload)

    return ContactService(
        queue_url="https://sqs.example/queue",
        enqueue=_enqueue,
    )


def _submission(**kwargs: str) -> ContactSubmission:
    defaults = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "category": "General Question",
        "subject": "Course access",
        "message": "Please help with login.",
        "honeypot": "",
    }
    defaults.update(kwargs)
    return ContactSubmission(**defaults)


class TestHoneypot:
    def test_non_empty_honeypot_accepted_without_enqueue(
        self, contact_svc: ContactService, sent_messages: List[Dict[str, Any]]
    ) -> None:
        contact_svc.submit(_submission(honeypot="filled-by-bot"))
        assert sent_messages == []

    def test_non_string_rs_hp_json_does_not_enqueue(
        self, contact_svc: ContactService, sent_messages: List[Dict[str, Any]]
    ) -> None:
        contact_svc.submit_from_dict({**_valid_dict(), "rs_hp": True})
        assert sent_messages == []


def _valid_dict() -> Dict[str, str]:
    return {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "category": "General Question",
        "subject": "Course access",
        "message": "Please help with login.",
    }


class TestEnqueuePayload:
    def test_success_enqueues_expected_sqs_json(
        self, contact_svc: ContactService, sent_messages: List[Dict[str, Any]]
    ) -> None:
        contact_svc.submit(_submission())
        assert len(sent_messages) == 1
        msg = sent_messages[0]
        assert msg["to"] == SUPPORT_INBOX
        assert msg["subject"] == "[Research Spectrum] General Question: Course access"
        assert msg["replyTo"] == "ada@example.com"
        assert "Ada Lovelace" in msg["bodyText"]
        assert "ada@example.com" in msg["bodyText"]
        assert "General Question" in msg["bodyText"]
        assert "Please help with login." in msg["bodyText"]

    def test_enqueue_failure_raises_service_unavailable(self) -> None:
        def _fail(_url: str, _payload: Dict[str, Any]) -> None:
            raise RuntimeError("sqs down")

        svc = ContactService(queue_url="https://sqs.example/queue", enqueue=_fail)
        with pytest.raises(ServiceUnavailable):
            svc.submit(_submission())


class TestMissingQueueUrl:
    def test_empty_queue_url_returns_503(self) -> None:
        svc = ContactService(queue_url="", enqueue=MagicMock())
        with pytest.raises(ServiceUnavailable, match="TRANSACTIONAL_MAIL_QUEUE_URL"):
            svc.submit(_submission())


class TestValidationDelegation:
    def test_invalid_submission_raises_bad_request(self, contact_svc: ContactService) -> None:
        with pytest.raises(BadRequest):
            contact_svc.submit_from_dict({"name": "only-name"})
