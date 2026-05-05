"""Session-end safety-net cleanup utilities. These are *not* the primary
cleanup path — per-test finalizers handle that. These helpers exist to leave
integration-test AWS resources tidy when a test crashes before its finalizer runs.

Course rows: leftovers are removed via the HTTP API (PostgreSQL catalog in
managed environments). No DynamoDB or direct database access from the runner.

Strictness policy: leftovers are logged but never fail the test session."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, List

import boto3
import httpx
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@dataclass
class CleanupReport:
    courses_removed_via_api: List[str]
    leftover_objects: List[str]

    def has_leftovers(self) -> bool:
        return bool(self.courses_removed_via_api) or bool(self.leftover_objects)

    def render_summary(self) -> str:
        lines = ["### Integration test cleanup report"]
        if not self.has_leftovers():
            lines.append("- No leftovers detected.")
            return "\n".join(lines)
        if self.courses_removed_via_api:
            lines.append(
                f"- Removed {len(self.courses_removed_via_api)} leftover courses via API (DELETE /courses/{{id}}):"
            )
            for cid in self.courses_removed_via_api[:20]:
                lines.append(f"  - `{cid}`")
            if len(self.courses_removed_via_api) > 20:
                lines.append(f"  - ... and {len(self.courses_removed_via_api) - 20} more")
        if self.leftover_objects:
            lines.append(f"- Removed {len(self.leftover_objects)} leftover S3 objects from the test video bucket:")
            for key in self.leftover_objects[:20]:
                lines.append(f"  - `{key}`")
            if len(self.leftover_objects) > 20:
                lines.append(f"  - ... and {len(self.leftover_objects) - 20} more")
        return "\n".join(lines)


def delete_prefixed_teacher_courses_via_http(
    *,
    api_base_url: str,
    auth_token: str,
    title_prefix: str,
    timeout_s: float = 30.0,
) -> List[str]:
    """DELETE every course owned by the token user whose title starts with *title_prefix*
    (``GET /courses/mine``, then ``DELETE /courses/{id}``). No direct DB access.

    Returns ids for which DELETE returned HTTP 200 (or 404 — already absent)."""
    base = api_base_url.strip().rstrip("/")
    token = auth_token.strip()
    if not base or not token:
        return []

    deleted_ids: List[str] = []
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base, headers=headers, timeout=timeout_s) as client:
        resp = client.get("/courses/mine")
        if resp.status_code != 200:
            logger.warning(
                "API safety-net list failed: GET /courses/mine -> %s %s",
                resp.status_code,
                (resp.text or "")[:500],
            )
            return []
        try:
            body: Any = resp.json()
        except Exception as e:
            logger.warning("API safety-net list: invalid JSON body: %s", e)
            return []
        if not isinstance(body, list):
            logger.warning(
                "API safety-net list: expected a JSON array, got %s", type(body).__name__
            )
            return []

        for item in body:
            if not isinstance(item, Mapping):
                continue
            title = str(item.get("title") or "")
            if not title.startswith(title_prefix):
                continue
            raw_id = item.get("id")
            if raw_id is None:
                continue
            course_id = str(raw_id).strip()
            if not course_id:
                continue
            del_resp = client.delete(f"/courses/{course_id}")
            if del_resp.status_code in (200, 404):
                deleted_ids.append(course_id)
            else:
                logger.warning(
                    "API safety-net delete failed for %s: HTTP %s",
                    course_id,
                    del_resp.status_code,
                )
    return deleted_ids


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
    """Delete every object in the integration-test video bucket (no prefix filter).

    CI targets non-prod **dev** buckets. There are no real users on these tiers,
    so a full-bucket sweep is acceptable after course-scoped S3 keys
    (`{courseId}/lessons/...`, `{courseId}/thumbnail/...`).

    SAFETY: Only empties buckets that match the StreamMyCourse **dev** video-bucket naming.
    **Production** is always refused.
    """
    if not bucket:
        return []

    import re

    dev_pattern = re.compile(r"^streammycourse-video-dev-.*videobucket")

    if "-prod-" in bucket:
        raise RuntimeError(
            f"REFUSING to empty bucket '{bucket}': "
            "This appears to be a prod bucket. "
            "Full-bucket cleanup must not run against production."
        )

    if dev_pattern.match(bucket):
        logger.info("Confirmed dev video bucket pattern. Proceeding with cleanup: %s", bucket)
    else:
        raise RuntimeError(
            f"REFUSING to empty bucket '{bucket}': "
            "Bucket must match 'streammycourse-video-dev-*videobucket*'. "
            "Full-bucket cleanup is only for non-prod integration test buckets."
        )
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
    bucket: str,
    region: str,
    title_prefix: str,
) -> CleanupReport:
    courses_api: List[str] = []
    leftover_objects: List[str] = []

    api_base = os.environ.get("INTEGRATION_API_BASE_URL", "").strip().rstrip("/")
    jwt = os.environ.get("INTEGRATION_COGNITO_JWT", "").strip()

    if api_base and jwt:
        try:
            courses_api = delete_prefixed_teacher_courses_via_http(
                api_base_url=api_base,
                auth_token=jwt,
                title_prefix=title_prefix,
            )
        except Exception as e:
            logger.warning("HTTP safety-net course cleanup failed: %s", e)
    else:
        logger.warning(
            "INTEGRATION_API_BASE_URL and INTEGRATION_COGNITO_JWT must both be set "
            "for session course cleanup; skipping API sweep."
        )

    try:
        leftover_objects = empty_entire_bucket(bucket, region=region)
    except Exception as e:
        logger.warning("S3 safety-net cleanup failed: %s", e)
    return CleanupReport(
        courses_removed_via_api=courses_api,
        leftover_objects=leftover_objects,
    )
