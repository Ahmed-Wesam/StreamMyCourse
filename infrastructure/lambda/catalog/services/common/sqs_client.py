"""Thin SQS helper for async media cleanup (catalog Lambda only sends messages)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional, Protocol

from services.common.errors import BadRequest

logger = logging.getLogger(__name__)


class _SQSClientProtocol(Protocol):
    def send_message(self, **kwargs: Any) -> Any: ...


def send_media_cleanup_job(
    queue_url: str,
    course_id: str,
    keys: List[str],
    *,
    sqs_client: Optional[_SQSClientProtocol] = None,
) -> None:
    """Enqueue one message per course with all S3 keys. Propagates SQS API errors."""
    if not keys:
        return
    if not queue_url:
        raise BadRequest("Media cleanup queue URL is required when keys are non-empty")
    client = sqs_client
    if client is None:
        import boto3

        client = boto3.client("sqs")

    payload = {
        "courseId": course_id,
        "keys": keys,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    ts = payload["timestamp"]
    max_bytes = 240 * 1024  # headroom below SQS 256 KiB limit
    chunks = list(_chunk_keys_for_messages(course_id, keys, ts, max_bytes))
    total_chunks = len(chunks)
    for idx, part in enumerate(chunks):
        part_body = json.dumps({"courseId": course_id, "keys": part, "timestamp": ts})
        try:
            _send_one(client, queue_url, part_body)
        except Exception:
            url_log = (queue_url[:64] + "...") if len(queue_url) > 64 else queue_url
            logger.error(
                "media_cleanup_sqs_partial_send: failed on chunk %s of %s (course_id=%s queue_url_prefix=%s)",
                idx + 1,
                total_chunks,
                course_id,
                url_log,
                exc_info=True,
            )
            raise


def _chunk_keys_for_messages(course_id: str, keys: List[str], timestamp: str, max_bytes: int) -> List[List[str]]:
    """Split keys into multiple message bodies that each fit under ``max_bytes``."""
    chunks: List[List[str]] = []
    current: List[str] = []
    for key in keys:
        trial_keys = current + [key]
        trial = {"courseId": course_id, "keys": trial_keys, "timestamp": timestamp}
        if len(json.dumps(trial).encode("utf-8")) <= max_bytes:
            current = trial_keys
            continue
        if current:
            chunks.append(current)
            current = []
        solo = {"courseId": course_id, "keys": [key], "timestamp": timestamp}
        if len(json.dumps(solo).encode("utf-8")) > max_bytes:
            raise BadRequest("An object key is too large to fit in an SQS media-cleanup message")
        current = [key]
    if current:
        chunks.append(current)
    return chunks


def _send_one(client: _SQSClientProtocol, queue_url: str, body: str) -> None:
    client.send_message(QueueUrl=queue_url, MessageBody=body)
