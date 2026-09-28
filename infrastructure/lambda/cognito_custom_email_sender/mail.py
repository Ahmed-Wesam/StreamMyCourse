"""Send transactional mail via Zoho SMTP."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

from smtp_config import ZohoSmtpConfig


class SmtpConnection(Protocol):
    def send_message(self, msg: EmailMessage) -> object: ...


def build_message(
    *,
    cfg: ZohoSmtpConfig,
    to_address: str,
    subject: str,
    body_text: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = cfg.from_address
    msg["To"] = to_address
    msg["Reply-To"] = cfg.reply_to
    msg["Subject"] = subject
    msg.set_content(body_text)
    return msg


def send_via_zoho_smtp(
    *,
    cfg: ZohoSmtpConfig,
    to_address: str,
    subject: str,
    body_text: str,
    smtp_factory: type[smtplib.SMTP] = smtplib.SMTP,
) -> None:
    to_address = to_address.strip()
    if not to_address:
        raise ValueError("Recipient email is required")
    msg = build_message(cfg=cfg, to_address=to_address, subject=subject, body_text=body_text)
    with smtp_factory(cfg.host, cfg.port, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(cfg.username, cfg.password)
        smtp.send_message(msg)
