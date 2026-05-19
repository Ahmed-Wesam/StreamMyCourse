"""SQS enqueue for billing domain events (WS3 — boto3 allowed here only)."""

from __future__ import annotations

import json
from typing import Any, List

import boto3

from domain.events import BillingDomainEvent

_PROVIDER = "paytabs"


class EnqueueError(Exception):
    """Raised when SQS SendMessage fails."""


def enqueue_domain_events(
    events: List[BillingDomainEvent],
    *,
    queue_url: str,
    sqs_client: Any | None = None,
) -> None:
    """Send domain events sequentially; raise on first failure."""
    if not queue_url:
        raise EnqueueError("FULFILLMENT_QUEUE_URL is not configured")

    client = sqs_client if sqs_client is not None else boto3.client("sqs")

    for event in events:
        body = json.dumps(event.to_sqs_dict(), separators=(",", ":"))
        try:
            response = client.send_message(QueueUrl=queue_url, MessageBody=body)
        except Exception as exc:  # noqa: BLE001 — propagate as EnqueueError for handler
            raise EnqueueError(str(exc)) from exc

        status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        message_id = response.get("MessageId")
        if not message_id or (status is not None and int(status) >= 400):
            raise EnqueueError("SQS SendMessage did not return MessageId")
