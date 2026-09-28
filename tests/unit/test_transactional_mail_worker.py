"""Unit tests for transactional_mail SQS worker (Zoho SMTP)."""

from __future__ import annotations

import importlib.util
import json
import sys
from email.message import EmailMessage
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LAMBDA_DIR = _REPO_ROOT / "infrastructure" / "lambda" / "transactional_mail"

SUPPORT_TO = "support@researchspectrum.org"


def _load_module(name: str, filename: str) -> ModuleType:
    lambda_dir = str(_LAMBDA_DIR)
    if lambda_dir not in sys.path:
        sys.path.insert(0, lambda_dir)
    path = _LAMBDA_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def smtp_config_mod() -> ModuleType:
    return _load_module("tm_smtp_config", "smtp_config.py")


@pytest.fixture
def mail_mod() -> ModuleType:
    return _load_module("tm_mail", "mail.py")


@pytest.fixture
def worker_mod(smtp_config_mod: ModuleType, mail_mod: ModuleType) -> ModuleType:
    # worker.py uses `from mail import` / `from smtp_config import` (Lambda zip layout).
    sys.modules["smtp_config"] = smtp_config_mod
    sys.modules["mail"] = mail_mod
    return _load_module("tm_worker", "worker.py")


@pytest.fixture
def zoho_cfg(smtp_config_mod: ModuleType) -> Any:
    return smtp_config_mod.ZohoSmtpConfig(
        host="smtp.zoho.com",
        port=587,
        username="noreply@researchspectrum.org",
        password="super-secret-smtp-password",
        from_address="Research Spectrum <noreply@researchspectrum.org>",
        reply_to=SUPPORT_TO,
    )


class RecordingSmtpFactory:
    """Captures SMTP instances and messages passed to send_message."""

    instances: list[RecordingSmtpFactory] = []
    sent_messages: list[EmailMessage] = []

    def __init__(self, host: str, port: int, timeout: float = 20) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.send_message = MagicMock(side_effect=self._record_send)
        RecordingSmtpFactory.instances.append(self)

    def _record_send(self, msg: EmailMessage) -> object:
        RecordingSmtpFactory.sent_messages.append(msg)
        return {}

    def __enter__(self) -> RecordingSmtpFactory:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def ehlo(self) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, username: str, password: str) -> None:
        return None

    @classmethod
    def reset(cls) -> None:
        cls.instances = []
        cls.sent_messages = []


def test_visitor_reply_to_becomes_reply_to_header(
    mail_mod: ModuleType, zoho_cfg: Any
) -> None:
    RecordingSmtpFactory.reset()
    visitor = "visitor@example.com"
    mail_mod.send_transactional_mail(
        cfg=zoho_cfg,
        to_address=SUPPORT_TO,
        subject="Contact form",
        body_text="Hello from visitor",
        reply_to=visitor,
        smtp_factory=RecordingSmtpFactory,  # type: ignore[arg-type]
    )
    assert RecordingSmtpFactory.sent_messages
    msg = RecordingSmtpFactory.sent_messages[0]
    assert msg["Reply-To"] == visitor


def test_omitted_reply_to_uses_secret_default(
    mail_mod: ModuleType, zoho_cfg: Any
) -> None:
    RecordingSmtpFactory.reset()
    mail_mod.send_transactional_mail(
        cfg=zoho_cfg,
        to_address=SUPPORT_TO,
        subject="Contact form",
        body_text="No custom reply",
        reply_to=None,
        smtp_factory=RecordingSmtpFactory,  # type: ignore[arg-type]
    )
    msg = RecordingSmtpFactory.sent_messages[0]
    assert msg["Reply-To"] == zoho_cfg.reply_to


def test_crlf_in_subject_raises_and_does_not_send(
    mail_mod: ModuleType, zoho_cfg: Any
) -> None:
    RecordingSmtpFactory.reset()
    with pytest.raises(ValueError, match="subject"):
        mail_mod.send_transactional_mail(
            cfg=zoho_cfg,
            to_address=SUPPORT_TO,
            subject="Bad\r\nSubject",
            body_text="body",
            smtp_factory=RecordingSmtpFactory,  # type: ignore[arg-type]
        )
    assert not RecordingSmtpFactory.instances


def test_crlf_in_reply_to_raises_and_does_not_send(
    mail_mod: ModuleType, zoho_cfg: Any
) -> None:
    RecordingSmtpFactory.reset()
    with pytest.raises(ValueError, match="reply"):
        mail_mod.send_transactional_mail(
            cfg=zoho_cfg,
            to_address=SUPPORT_TO,
            subject="Ok subject",
            body_text="body",
            reply_to="evil@example.com\nBcc: attacker@evil.com",
            smtp_factory=RecordingSmtpFactory,  # type: ignore[arg-type]
        )
    assert not RecordingSmtpFactory.instances


def test_disallowed_to_raises_and_does_not_call_smtp(
    mail_mod: ModuleType, zoho_cfg: Any
) -> None:
    RecordingSmtpFactory.reset()
    with pytest.raises(ValueError, match="allowlist"):
        mail_mod.send_transactional_mail(
            cfg=zoho_cfg,
            to_address="attacker@example.com",
            subject="Hi",
            body_text="body",
            smtp_factory=RecordingSmtpFactory,  # type: ignore[arg-type]
        )
    assert not RecordingSmtpFactory.instances


def test_worker_handler_sends_allowlisted_message(
    worker_mod: ModuleType, mail_mod: ModuleType, zoho_cfg: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    RecordingSmtpFactory.reset()
    sent: list[tuple[str, str, str, str | None]] = []

    def fake_send(**kwargs: Any) -> None:
        sent.append(
            (
                kwargs["to_address"],
                kwargs["subject"],
                kwargs["body_text"],
                kwargs.get("reply_to"),
            )
        )

    monkeypatch.setattr(worker_mod, "load_zoho_smtp_config", lambda **_: zoho_cfg)
    monkeypatch.setattr(worker_mod, "send_transactional_mail", fake_send)

    body = {
        "to": SUPPORT_TO,
        "subject": "Question",
        "bodyText": "Need help",
        "replyTo": "student@school.edu",
    }
    event = {"Records": [{"messageId": "m1", "body": json.dumps(body)}]}
    out = worker_mod.lambda_handler(event, None)
    assert out == {"batchItemFailures": []}
    assert sent == [(SUPPORT_TO, "Question", "Need help", "student@school.edu")]


def test_worker_rejects_non_allowlisted_to(
    worker_mod: ModuleType, zoho_cfg: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    RecordingSmtpFactory.reset()
    monkeypatch.setattr(worker_mod, "load_zoho_smtp_config", lambda **_: zoho_cfg)
    real_send = worker_mod.send_transactional_mail

    def send_with_fake_smtp(**kwargs: Any) -> None:
        kwargs["smtp_factory"] = RecordingSmtpFactory  # type: ignore[assignment]
        return real_send(**kwargs)

    monkeypatch.setattr(worker_mod, "send_transactional_mail", send_with_fake_smtp)

    body = {
        "to": "other@example.com",
        "subject": "Hi",
        "bodyText": "secret-body-content",
    }
    event = {"Records": [{"messageId": "m-bad", "body": json.dumps(body)}]}
    out = worker_mod.lambda_handler(event, None)
    assert out == {"batchItemFailures": [{"itemIdentifier": "m-bad"}]}
    assert not RecordingSmtpFactory.instances


def test_logs_do_not_contain_body_subject_or_password(
    worker_mod: ModuleType,
    mail_mod: ModuleType,
    zoho_cfg: Any,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.INFO)
    RecordingSmtpFactory.reset()
    monkeypatch.setattr(worker_mod, "load_zoho_smtp_config", lambda **_: zoho_cfg)
    real_send = worker_mod.send_transactional_mail

    def send_with_fake_smtp(**kwargs: Any) -> None:
        kwargs["smtp_factory"] = RecordingSmtpFactory  # type: ignore[assignment]
        return real_send(**kwargs)

    monkeypatch.setattr(worker_mod, "send_transactional_mail", send_with_fake_smtp)

    sensitive_subject = "Sensitive subject line"
    sensitive_body = "super-secret-body-text-xyz"
    body = {
        "to": SUPPORT_TO,
        "subject": sensitive_subject,
        "bodyText": sensitive_body,
    }
    event = {"Records": [{"messageId": "m-log", "body": json.dumps(body)}]}
    worker_mod.lambda_handler(event, None)

    log_blob = caplog.text
    assert zoho_cfg.password not in log_blob
    assert sensitive_body not in log_blob
    assert sensitive_subject not in log_blob
