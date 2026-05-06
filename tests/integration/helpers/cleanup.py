"""Session-end safety-net cleanup utilities. These are *not* the primary
cleanup path — per-test finalizers handle that. These helpers exist to leave
integration-test AWS resources tidy when a test crashes before its finalizer runs.

Course rows: leftovers are removed via the HTTP API (PostgreSQL catalog in
managed environments). No DynamoDB or direct database access from the runner.

Strictness policy: leftovers are logged but never fail the test session."""

from __future__ import annotations

import logging
import os
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, List, Tuple

import boto3
import httpx
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def log_integration_cleanup_error(message: str) -> None:
    """Log at ERROR and emit a GitHub Actions ``::error::`` so skipped S3 cleanup surfaces in CI."""
    logger.error("integration_cleanup: %s", message)
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        safe = (
            message.replace("%", "%25")
            .replace("\r", "%0D")
            .replace("\n", "%0A")
        )
        sys.stderr.write(f"::error::integration_cleanup: {safe}\n")
        sys.stderr.flush()


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


_UUID_COURSE_ID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def delete_prefixed_teacher_courses_via_http(
    *,
    api_base_url: str,
    auth_token: str,
    title_prefix: str,
    timeout_s: float = 30.0,
) -> Tuple[List[str], List[str]]:
    """DELETE every course owned by the token user whose title starts with *title_prefix*
    (``GET /courses/mine``, then ``DELETE /courses/{id}``). No direct DB access.

    Returns ``(deleted_ids, matched_ids)`` where *matched_ids* are every course id whose
    title matched the prefix (used to scope S3 prefix cleanup). *deleted_ids* are ids for
    which DELETE returned HTTP 200 (or 404 — already absent)."""
    base = api_base_url.strip().rstrip("/")
    token = auth_token.strip()
    if not base or not token:
        return [], []

    deleted_ids: List[str] = []
    matched_ids: List[str] = []
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=base, headers=headers, timeout=timeout_s) as client:
        resp = client.get("/courses/mine")
        if resp.status_code != 200:
            log_integration_cleanup_error(
                f"API safety-net list failed: GET /courses/mine -> {resp.status_code} "
                f"{(resp.text or '')[:500]!r}; no S3 prefix cleanup will run for matched courses."
            )
            return [], []
        try:
            body: Any = resp.json()
        except Exception as e:
            log_integration_cleanup_error(
                f"API safety-net list: invalid JSON body ({e!r}); no S3 prefix cleanup will run."
            )
            return [], []
        if not isinstance(body, list):
            log_integration_cleanup_error(
                "API safety-net list: expected a JSON array, got "
                f"{type(body).__name__}; no S3 prefix cleanup will run."
            )
            return [], []

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
            matched_ids.append(course_id)
            del_resp = client.delete(f"/courses/{course_id}")
            if del_resp.status_code in (200, 404):
                deleted_ids.append(course_id)
            else:
                log_integration_cleanup_error(
                    f"API safety-net DELETE /courses/{course_id} failed with HTTP "
                    f"{del_resp.status_code}; catalog row may remain and S3 prefix cleanup still runs."
                )
    return deleted_ids, matched_ids


def _assert_dev_integration_video_bucket(bucket: str) -> None:
    """Raise if *bucket* is not the known dev integration video-bucket name pattern."""
    if not bucket:
        raise RuntimeError("REFUSING: empty bucket name")

    dev_pattern = re.compile(r"^streammycourse-video-dev-.*videobucket")

    if "-prod-" in bucket:
        raise RuntimeError(
            f"REFUSING to operate on bucket '{bucket}': "
            "This appears to be a prod bucket. "
            "Integration cleanup must not run against production."
        )

    if dev_pattern.match(bucket):
        return

    raise RuntimeError(
        f"REFUSING to operate on bucket '{bucket}': "
        "Bucket must match 'streammycourse-video-dev-*videobucket*'. "
        "Integration S3 cleanup is only for the non-prod dev video bucket."
    )


def delete_all_objects_under_prefix(bucket: str, *, region: str, prefix: str) -> List[str]:
    """List and delete every object whose key starts with *prefix* (prefix must be non-empty)."""
    if not bucket or not prefix or ".." in prefix or prefix.startswith("/"):
        return []
    s3 = boto3.client("s3", region_name=region)
    deleted_keys: List[str] = []
    continuation: str | None = None
    while True:
        kwargs: dict[str, Any] = {"Bucket": bucket, "Prefix": prefix}
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


def delete_orphan_media_for_course_prefixes(
    bucket: str, *, region: str, course_ids: List[str]
) -> List[str]:
    """Delete S3 objects only under ``{courseId}/`` for each UUID in *course_ids*.

    Used after the HTTP safety net so shared dev buckets keep non-test objects.
    """
    if not course_ids:
        return []
    _assert_dev_integration_video_bucket(bucket)
    deleted: List[str] = []
    skipped_non_uuid: List[str] = []
    for raw in course_ids:
        cid = (raw or "").strip()
        if not _UUID_COURSE_ID.match(cid):
            skipped_non_uuid.append(repr(raw))
            continue
        deleted.extend(delete_all_objects_under_prefix(bucket, region=region, prefix=f"{cid}/"))
    if skipped_non_uuid:
        log_integration_cleanup_error(
            "S3 safety-net refused to delete objects for non-UUID course id(s) "
            f"(cannot use course-scoped S3 prefix): {', '.join(skipped_non_uuid)}"
        )
    return deleted


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
    """Delete every object in the bucket (no prefix filter).

    .. warning::
        **Destructive.** Session cleanup uses :func:`delete_orphan_media_for_course_prefixes`
        instead so shared dev buckets are not wiped. Keep this for rare manual recovery only.

    SAFETY: Only empties buckets that match the StreamMyCourse **dev** video-bucket naming.
    **Production** is always refused.
    """
    if not bucket:
        return []

    _assert_dev_integration_video_bucket(bucket)
    logger.warning(
        "empty_entire_bucket: full-bucket delete on %s (prefer scoped cleanup)", bucket
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
    """Delete only objects under *prefix* (default ``uploads/``) in the dev integration bucket."""
    _assert_dev_integration_video_bucket(bucket)
    return delete_all_objects_under_prefix(bucket, region=region, prefix=prefix)


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

    matched_course_ids: List[str] = []
    if api_base and jwt:
        try:
            courses_api, matched_course_ids = delete_prefixed_teacher_courses_via_http(
                api_base_url=api_base,
                auth_token=jwt,
                title_prefix=title_prefix,
            )
        except Exception as e:
            log_integration_cleanup_error(
                f"HTTP safety-net course cleanup raised ({e!r}); "
                "matched course ids unknown — no scoped S3 prefix cleanup."
            )
            courses_api = []
            matched_course_ids = []
    else:
        log_integration_cleanup_error(
            "INTEGRATION_API_BASE_URL and INTEGRATION_COGNITO_JWT must both be set "
            f"for session cleanup (bucket={bucket!r} is configured); "
            "skipping API sweep and scoped S3 deletes — leftover test objects may remain."
        )
        courses_api = []
        matched_course_ids = []

    try:
        leftover_objects = delete_orphan_media_for_course_prefixes(
            bucket, region=region, course_ids=matched_course_ids
        )
    except Exception as e:
        log_integration_cleanup_error(f"S3 safety-net cleanup failed: {e!r}")
    return CleanupReport(
        courses_removed_via_api=courses_api,
        leftover_objects=leftover_objects,
    )
