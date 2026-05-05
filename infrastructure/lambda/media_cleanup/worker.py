"""SQS-triggered Lambda: batch-delete S3 objects listed in each message."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

_s3 = boto3.client("s3")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    bucket = (os.environ.get("VIDEO_BUCKET") or "").strip()
    records = event.get("Records") or []
    if not bucket:
        logger.error(
            "VIDEO_BUCKET is not configured; failing entire SQS batch so messages are not lost"
        )
        failures = [
            {"itemIdentifier": mid}
            for r in records
            if (mid := (r.get("messageId") or "").strip())
        ]
        return {"batchItemFailures": failures}

    failures: List[Dict[str, str]] = []
    for record in event.get("Records") or []:
        mid = record.get("messageId") or ""
        try:
            body = json.loads(record.get("body") or "{}")
            keys = body.get("keys") or []
            course_id = str(body.get("courseId") or "")
            _delete_keys_for_message(bucket, keys, course_id=course_id, message_id=mid)
        except Exception:
            logger.exception("Failed processing SQS message %s", mid)
            if mid:
                failures.append({"itemIdentifier": mid})

    return {"batchItemFailures": failures}


def _delete_keys_for_message(bucket: str, keys: List[Any], *, course_id: str, message_id: str) -> None:
    deduped = list(dict.fromkeys(str(k).strip() for k in keys if str(k).strip()))
    if not deduped:
        return
    deleted = 0
    for i in range(0, len(deduped), 1000):
        chunk = deduped[i : i + 1000]
        resp = _s3.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True},
        )
        errs = resp.get("Errors") or []
        if errs:
            logger.warning(
                "S3 delete_objects reported errors course=%s msg=%s errors=%s",
                course_id,
                message_id,
                errs,
            )
            raise RuntimeError("S3 partial delete failure")
        deleted += len(chunk)
    logger.info(
        "Media cleanup completed course=%s message=%s deleted_objects=%d",
        course_id,
        message_id,
        deleted,
    )
