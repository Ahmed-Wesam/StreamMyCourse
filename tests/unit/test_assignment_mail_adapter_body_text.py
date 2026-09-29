"""RS-14 slice 1: assignment mail adapter must send bodyText (not body)."""

from __future__ import annotations

from unittest.mock import MagicMock

import bootstrap as bootstrap_mod
from services.assignments.ports import NotifyMailMessage


def test_assignment_mail_adapter_payload_uses_body_text_not_body(monkeypatch) -> None:
    captured: dict = {}

    def fake_send(queue_url: str, message: dict, *, sqs_client=None) -> None:
        captured["queue_url"] = queue_url
        captured["message"] = message

    monkeypatch.setattr(bootstrap_mod, "send_transactional_mail_job", fake_send)

    adapter = bootstrap_mod._AssignmentMailAdapter("https://sqs.example/mail")
    adapter.enqueue_notify(
        NotifyMailMessage(
            kind="notify",
            to="student@example.com",
            subject="Grade result",
            body="You passed.\nFeedback here.",
        )
    )

    payload = captured["message"]
    assert payload["kind"] == "notify"
    assert payload["to"] == "student@example.com"
    assert payload["subject"] == "Grade result"
    assert "bodyText" in payload
    assert payload["bodyText"]
    assert "body" not in payload
