"""Session-end safety-net cleanup utilities. These are *not* the primary
cleanup path -- per-test finalizers handle that. These helpers exist to keep
integ AWS resources tidy when a test crashes before its finalizer runs.

Strictness policy: leftovers are logged but never fail the test session."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)


@dataclass
class CleanupReport:
    leftover_courses: List[str]
    leftover_objects: List[str]

    def has_leftovers(self) -> bool:
        return bool(self.leftover_courses) or bool(self.leftover_objects)

    def render_summary(self) -> str:
        lines = ["### Integ test cleanup report"]
        if not self.has_leftovers():
            lines.append("- No leftovers detected.")
            return "\n".join(lines)
        if self.leftover_courses:
            lines.append(f"- Removed {len(self.leftover_courses)} leftover course rows from DynamoDB:")
            for cid in self.leftover_courses[:20]:
                lines.append(f"  - `{cid}`")
            if len(self.leftover_courses) > 20:
                lines.append(f"  - ... and {len(self.leftover_courses) - 20} more")
        if self.leftover_objects:
            lines.append(f"- Removed {len(self.leftover_objects)} leftover S3 objects from the integ video bucket:")
            for key in self.leftover_objects[:20]:
                lines.append(f"  - `{key}`")
            if len(self.leftover_objects) > 20:
                lines.append(f"  - ... and {len(self.leftover_objects) - 20} more")
        return "\n".join(lines)


def truncate_test_courses(table_name: str, *, region: str, title_prefix: str) -> List[str]:
    """Scan the integ table for test-prefixed courses and delete every row
    (course metadata + all its lessons). Returns deleted course ids."""
    if not table_name:
        return []
    ddb = boto3.resource("dynamodb", region_name=region)
    table = ddb.Table(table_name)

    # Find COURSE# metadata rows whose title begins with the test prefix.
    course_pks: List[str] = []
    scan_kwargs = {
        "FilterExpression": Attr("PK").begins_with("COURSE#")
        & Attr("SK").eq("METADATA")
        & Attr("title").begins_with(title_prefix),
    }
    while True:
        resp = table.scan(**scan_kwargs)
        for item in resp.get("Items", []):
            pk = str(item.get("PK", ""))
            if pk:
                course_pks.append(pk)
        if "LastEvaluatedKey" not in resp:
            break
        scan_kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    deleted_course_ids: List[str] = []
    for pk in course_pks:
        # Delete metadata + all LESSON# rows for this course.
        course_id = pk.replace("COURSE#", "")
        keys_to_delete: List[dict] = [{"PK": pk, "SK": "METADATA"}]
        from boto3.dynamodb.conditions import Key

        q = table.query(KeyConditionExpression=Key("PK").eq(pk) & Key("SK").begins_with("LESSON#"))
        for lesson_item in q.get("Items", []):
            keys_to_delete.append({"PK": pk, "SK": str(lesson_item["SK"])})

        with table.batch_writer() as batch:
            for key in keys_to_delete:
                batch.delete_item(Key=key)
        deleted_course_ids.append(course_id)

    return deleted_course_ids


def s3_object_exists(bucket: str, key: str, *, region: str) -> bool:
    """Return True if the object exists (HeadObject succeeds)."""
    if not bucket or not key:
        return False
    s3 = boto3.client("s3", region_name=region)
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        code = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        err_code = e.response.get("Error", {}).get("Code", "")
        if code == 404 or err_code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def empty_entire_bucket(bucket: str, *, region: str) -> List[str]:
    """Delete every object in the integ video bucket (no prefix filter).

    Integ has no real users so a full-bucket sweep is safe after course-scoped
    S3 keys (`{courseId}/lessons/...`, `{courseId}/thumbnail/...`).
    """
    if not bucket:
        return []
    s3 = boto3.client("s3", region_name=region)
    deleted_keys: List[str] = []
    continuation: str | None = None
    while True:
        kwargs: dict = {"Bucket": bucket}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        resp = s3.list_objects_v2(**kwargs)
        contents = resp.get("Contents", []) or []
        if contents:
            objects = [{"Key": obj["Key"]} for obj in contents]
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True})
            deleted_keys.extend(o["Key"] for o in objects)
        if not resp.get("IsTruncated"):
            break
        continuation = resp.get("NextContinuationToken")
    return deleted_keys


def empty_uploads_prefix(bucket: str, *, region: str, prefix: str = "uploads/") -> List[str]:
    """Deprecated: use ``empty_entire_bucket``. Kept for callers that still pass a prefix."""
    _ = prefix
    return empty_entire_bucket(bucket, region=region)


def run_safety_net(
    *,
    table_name: str,
    bucket: str,
    region: str,
    title_prefix: str,
) -> CleanupReport:
    leftover_courses: List[str] = []
    leftover_objects: List[str] = []
    try:
        leftover_courses = truncate_test_courses(table_name, region=region, title_prefix=title_prefix)
    except Exception as e:
        logger.warning("DynamoDB safety-net cleanup failed: %s", e)
    try:
        leftover_objects = empty_entire_bucket(bucket, region=region)
    except Exception as e:
        logger.warning("S3 safety-net cleanup failed: %s", e)
    return CleanupReport(leftover_courses=leftover_courses, leftover_objects=leftover_objects)
