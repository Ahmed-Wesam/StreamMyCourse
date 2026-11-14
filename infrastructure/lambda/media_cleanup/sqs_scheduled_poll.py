"""Poll SQS on an EventBridge schedule instead of always-on ESM long polls.

EventBridge cannot fire faster than once a minute. Each run checks the queue
four times, 15 seconds apart, so a message waits at most about 15 seconds.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Optional

import boto3

_sqs: Optional[Any] = None


def _sqs_client() -> Any:
    """Create the client on first use. Import must not require AWS_REGION (unit tests)."""
    global _sqs
    if _sqs is None:
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "eu-west-1"
        _sqs = boto3.client("sqs", region_name=region)
    return _sqs


POLL_MAX_MESSAGES = 10
POLL_INTERVAL_SECONDS = 15
POLL_PASSES = 4


def should_poll_queue(event: Dict[str, Any]) -> bool:
    return "Records" not in event


def poll_queue_records(queue_url: str) -> List[Dict[str, Any]]:
    url = (queue_url or "").strip()
    if not url:
        raise RuntimeError("WORK_QUEUE_URL is not configured")

    resp = _sqs_client().receive_message(
        QueueUrl=url,
        MaxNumberOfMessages=POLL_MAX_MESSAGES,
        WaitTimeSeconds=0,
        AttributeNames=["All"],
        MessageAttributeNames=["All"],
    )
    records: List[Dict[str, Any]] = []
    for msg in resp.get("Messages") or []:
        mid = msg.get("MessageId") or ""
        records.append(
            {
                "messageId": mid,
                "body": msg.get("Body") or "",
                "eventSource": "aws:sqs",
                "_receiptHandle": msg.get("ReceiptHandle") or "",
            }
        )
    return records


def run_scheduled_polls(
    queue_url: str,
    handle_batch: Callable[[List[Dict[str, Any]]], List[Dict[str, str]]],
    *,
    sleeper: Callable[[float], None] = time.sleep,
) -> List[Dict[str, str]]:
    """Receive and handle up to four batches, 15 seconds apart. Empty checks do not call handle_batch."""
    failures: List[Dict[str, str]] = []
    for index in range(POLL_PASSES):
        if index:
            sleeper(POLL_INTERVAL_SECONDS)
        records = poll_queue_records(queue_url)
        if not records:
            continue
        batch_failures = handle_batch(records)
        delete_processed_messages(
            queue_url=queue_url,
            records=records,
            failures=batch_failures,
        )
        failures.extend(batch_failures)
    return failures


def delete_processed_messages(
    *,
    queue_url: str,
    records: List[Dict[str, Any]],
    failures: List[Dict[str, str]],
) -> None:
    url = (queue_url or "").strip()
    if not url or not records:
        return
    failed = {f.get("itemIdentifier") for f in failures if f.get("itemIdentifier")}
    for record in records:
        mid = record.get("messageId") or ""
        if mid in failed:
            continue
        rh = str(record.get("_receiptHandle") or "")
        if not rh:
            continue
        _sqs_client().delete_message(QueueUrl=url, ReceiptHandle=rh)