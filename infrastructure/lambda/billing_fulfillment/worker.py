"""SQS-triggered billing fulfillment stub (WS2): log body, no RDS writes until WS3."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    for record in event.get("Records") or []:
        message_id = record.get("messageId") or ""
        body = record.get("body") or ""
        logger.info(
            "Billing fulfillment stub message_id=%s body=%s",
            message_id,
            body,
        )
    return {"batchItemFailures": []}
