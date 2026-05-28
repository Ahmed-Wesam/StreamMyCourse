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
    s3_keys: Optional[List[str]] = None,
    kinescope_video_ids: Optional[List[str]] = None,
    sqs_client: Optional[_SQSClientProtocol] = None,
) -> None:
    """Enqueue one or more cleanup messages. Propagates SQS API errors."""
    s3_keys = list(s3_keys if s3_keys is not None else keys)
    kinescope_video_ids = list(kinescope_video_ids or [])
    if not s3_keys and not kinescope_video_ids:
        return
    if not queue_url:
        raise BadRequest("Media cleanup queue URL is required when keys are non-empty")
    client = sqs_client
    if client is None:
        import boto3

        client = boto3.client("sqs")

    ts = datetime.now(timezone.utc).isoformat()
    max_bytes = 240 * 1024  # headroom below SQS 256 KiB limit
    messages = list(
        _build_messages(
            course_id=course_id,
            timestamp=ts,
            s3_keys=s3_keys,
            kinescope_video_ids=kinescope_video_ids,
            max_bytes=max_bytes,
        )
    )
    total_chunks = len(messages)
    for idx, part_body in enumerate(messages):
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


def _build_messages(
    *,
    course_id: str,
    timestamp: str,
    s3_keys: List[str],
    kinescope_video_ids: List[str],
    max_bytes: int,
) -> List[str]:
    messages: List[str] = []
    if s3_keys:
        for chunk in _chunk_keys_for_messages(course_id, s3_keys, timestamp, max_bytes):
            body = {
                "courseId": course_id,
                "timestamp": timestamp,
                "keys": chunk,
                "provider": "s3",
                "s3Keys": chunk,
            }
            messages.append(json.dumps(body))
    if kinescope_video_ids:
        for chunk in _chunk_kinescope_ids_for_messages(course_id, kinescope_video_ids, timestamp, max_bytes):
            body = {
                "courseId": course_id,
                "timestamp": timestamp,
                "provider": "kinescope",
                "kinescopeVideoIds": chunk,
            }
            messages.append(json.dumps(body))
    return messages


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


def _chunk_kinescope_ids_for_messages(
    course_id: str, video_ids: List[str], timestamp: str, max_bytes: int
) -> List[List[str]]:
    chunks: List[List[str]] = []
    current: List[str] = []
    for video_id in video_ids:
        trial_ids = current + [video_id]
        trial = {
            "courseId": course_id,
            "provider": "kinescope",
            "kinescopeVideoIds": trial_ids,
            "timestamp": timestamp,
        }
        if len(json.dumps(trial).encode("utf-8")) <= max_bytes:
            current = trial_ids
            continue
        if current:
            chunks.append(current)
            current = []
        solo = {
            "courseId": course_id,
            "provider": "kinescope",
            "kinescopeVideoIds": [video_id],
            "timestamp": timestamp,
        }
        if len(json.dumps(solo).encode("utf-8")) > max_bytes:
            raise BadRequest("A Kinescope video ID is too large to fit in an SQS media-cleanup message")
        current = [video_id]
    if current:
        chunks.append(current)
    return chunks


def _send_one(client: _SQSClientProtocol, queue_url: str, body: str) -> None:
    client.send_message(QueueUrl=queue_url, MessageBody=body)
