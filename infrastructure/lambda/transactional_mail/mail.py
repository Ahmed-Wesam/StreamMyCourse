"""Send transactional mail via Zoho SMTP."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

from smtp_config import ZohoSmtpConfig

ALLOWLIST_TO_ADDRESSES: frozenset[str] = frozenset({"support@researchspectrum.org"})


class SmtpConnection(Protocol):
    def send_message(self, msg: EmailMessage) -> object: ...


def _reject_crlf(value: str, field_name: str) -> None:
    if "\r" in value or "\n" in value:
        raise ValueError(f"{field_name} must not contain CR or LF")


def _normalize_kind(kind: str | None) -> str:
    raw = (kind or "").strip().lower()
    if not raw:
        return "contact"
    if raw in ("contact", "notify"):
        return raw
    raise ValueError(f"Unsupported mail kind {kind!r}")


def _validate_notify_recipient(to_address: str) -> str:
    addr = to_address.strip()
    if not addr:
        raise ValueError("Recipient is required")
    _reject_crlf(addr, "to")
    if "," in addr:
        raise ValueError("Notify recipient must be a single address")
    if any(ch.isspace() for ch in addr):
        raise ValueError("Notify recipient must be a single address")
    if "@" not in addr:
        raise ValueError("Notify recipient must be a single address")
    return addr


def build_message(
    *,
    cfg: ZohoSmtpConfig,
    to_address: str,
    subject: str,
    body_text: str,
    reply_to_header: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = cfg.from_address
    msg["To"] = to_address
    msg["Reply-To"] = reply_to_header
    msg["Subject"] = subject
    msg.set_content(body_text)
    return msg


def send_transactional_mail(
    *,
    cfg: ZohoSmtpConfig,
    to_address: str,
    subject: str,
    body_text: str,
    reply_to: str | None = None,
    kind: str | None = None,
    smtp_factory: type[smtplib.SMTP] = smtplib.SMTP,
) -> None:
    mail_kind = _normalize_kind(kind)
    to_address = to_address.strip()

    if mail_kind == "notify":
        to_address = _validate_notify_recipient(to_address)
    else:
        if to_address not in ALLOWLIST_TO_ADDRESSES:
            raise ValueError(f"Recipient {to_address!r} is not on the allowlist")

    _reject_crlf(subject, "subject")

    if reply_to is not None and str(reply_to).strip():
        reply_to_header = str(reply_to).strip()
        _reject_crlf(reply_to_header, "replyTo")
    else:
        reply_to_header = cfg.reply_to

    msg = build_message(
        cfg=cfg,
        to_address=to_address,
        subject=subject,
        body_text=body_text,
        reply_to_header=reply_to_header,
    )
    with smtp_factory(cfg.host, cfg.port, timeout=20) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(cfg.username, cfg.password)
        smtp.send_message(msg)
