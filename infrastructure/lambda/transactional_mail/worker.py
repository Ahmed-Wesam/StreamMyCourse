"""SQS-triggered Lambda: send transactional mail for each message body."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from mail import send_transactional_mail
from smtp_config import load_zoho_smtp_config

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    failures: List[Dict[str, str]] = []
    cfg = load_zoho_smtp_config()
    for record in event.get("Records") or []:
        mid = record.get("messageId") or ""
        try:
            body = json.loads(record.get("body") or "{}")
            _send_for_message(body=body, cfg=cfg, message_id=mid)
        except Exception:
            logger.exception("Failed processing transactional mail message %s", mid)
            if mid:
                failures.append({"itemIdentifier": mid})

    return {"batchItemFailures": failures}


def _send_for_message(*, body: Dict[str, Any], cfg: Any, message_id: str) -> None:
    to_address = str(body.get("to") or "").strip()
    subject = str(body.get("subject") or "")
    body_text = str(body.get("bodyText") or "")
    kind_raw = body.get("kind")
    kind: str | None
    if kind_raw is None:
        kind = None
    else:
        kind = str(kind_raw).strip() or None

    reply_to_raw = body.get("replyTo")
    reply_to: str | None
    if reply_to_raw is None:
        reply_to = None
    else:
        reply_to = str(reply_to_raw).strip() or None

    if not to_address:
        raise ValueError("SQS message field 'to' is required")
    if not subject:
        raise ValueError("SQS message field 'subject' is required")
    if body_text is None:
        raise ValueError("SQS message field 'bodyText' is required")

    send_transactional_mail(
        cfg=cfg,
        to_address=to_address,
        subject=subject,
        body_text=body_text,
        reply_to=reply_to,
        kind=kind,
    )

    normalized_kind = (kind or "").strip().lower() or "contact"
    if normalized_kind == "notify":
        logger.info(
            "Transactional mail sent message_id=%s kind=%s",
            message_id,
            normalized_kind,
        )
    else:
        logger.info(
            "Transactional mail sent message_id=%s to=%s",
            message_id,
            to_address,
        )
