from __future__ import annotations

import logging
import os
import re
from typing import List, Sequence
from uuid import uuid4

try:
    import boto3
    from botocore.config import Config
except Exception:  # pragma: no cover
    boto3 = None
    Config = None  # type: ignore[misc, assignment]

from services.common.errors import BadRequest
from services.course_management.models import PresignResult

logger = logging.getLogger(__name__)

_S3_DELETE_BATCH = 1000

# Presigned upload contracts (align with design.md upload limits / MIME safety)
MAX_VIDEO_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GiB (documented; S3 single PUT max 5 GiB)

ALLOWED_VIDEO_CONTENT_TYPES = frozenset(
    {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
)
ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
)

# UUID v4-style segment (hyphenated 8-4-4-4-12 hex); matches uuid4() string form.
_UUID_SEGMENT = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

_MEDIA_KEY_PATTERNS = (
    # Lesson video: {courseId}/lessons/{lessonId}/video/{uuid}.{ext}
    re.compile(
        rf"^({_UUID_SEGMENT})/lessons/({_UUID_SEGMENT})/video/({_UUID_SEGMENT})\.(mp4|webm|mov|avi)$"
    ),
    # Lesson thumbnail
    re.compile(
        rf"^({_UUID_SEGMENT})/lessons/({_UUID_SEGMENT})/thumbnail/({_UUID_SEGMENT})\.(jpg|png|webp|gif)$"
    ),
    # Course thumbnail
    re.compile(rf"^({_UUID_SEGMENT})/thumbnail/({_UUID_SEGMENT})\.(jpg|png|webp|gif)$"),
)


def _normalize_content_type(raw: str) -> str:
    t = (raw or "").strip().lower()
    if not t:
        return ""
    return t.split(";", 1)[0].strip()


def _extension_for_video_content_type(norm: str) -> str:
    mapping = {
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/quicktime": "mov",
        "video/x-msvideo": "avi",
    }
    ext = mapping.get(norm)
    if not ext:
        raise BadRequest("Invalid or unsupported video content type")
    return ext


def _extension_for_image_content_type(norm: str) -> str:
    mapping = {
        "image/jpeg": "jpg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    ext = mapping.get(norm)
    if not ext:
        raise BadRequest("Invalid or unsupported image content type")
    return ext


def _is_valid_media_object_key(key: str) -> bool:
    k = (key or "").strip()
    if not k or ".." in k or "//" in k or k.startswith("/"):
        return False
    return any(p.fullmatch(k) is not None for p in _MEDIA_KEY_PATTERNS)


def _s3_client():
    """Regional SigV4 client so presigned URLs use bucket.s3.<region>.amazonaws.com (not global SigV2)."""
    if boto3 is None or Config is None:
        raise RuntimeError("boto3 is not available")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "eu-west-1"
    cfg = Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
        # Cap unbounded hangs on delete_objects in VPC (can block same-request DB work).
        connect_timeout=5,
        read_timeout=15,
    )
    # Explicit regional endpoint avoids legacy SigV2-style URLs on s3.amazonaws.com (bad CORS preflight).
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://s3.{region}.amazonaws.com",
        config=cfg,
    )


class CourseMediaStorage:
    def __init__(self, video_bucket: str):
        if not video_bucket:
            raise RuntimeError("VIDEO_BUCKET is required for uploads")
        self._bucket = video_bucket
        self._s3 = _s3_client()

    @staticmethod
    def _require_video_content_type(content_type: str) -> str:
        norm = _normalize_content_type(content_type)
        if norm not in ALLOWED_VIDEO_CONTENT_TYPES:
            raise BadRequest("Invalid or unsupported video content type")
        return norm

    @staticmethod
    def _require_image_content_type(content_type: str) -> str:
        norm = _normalize_content_type(content_type)
        if norm not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise BadRequest("Invalid or unsupported image content type")
        return norm

    def presign_put(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> PresignResult:
        _ = filename  # kept for API / port compatibility; key uses uuid + extension only
        ctype = self._require_video_content_type(content_type)
        ext = _extension_for_video_content_type(ctype)
        cid = (course_id or "").strip()
        lid = (lesson_id or "").strip()
        if not cid or not lid or "/" in cid or "/" in lid:
            raise BadRequest("Invalid course or lesson id for upload")
        video_key = f"{cid}/lessons/{lid}/video/{uuid4()}.{ext}"
        # boto3 generate_presigned_url does not support policy Conditions (e.g.
        # content-length-range on PUT). Documented max upload size is MAX_VIDEO_UPLOAD_BYTES;
        # S3 also caps single PUT at 5 GiB.
        upload_url = self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket, "Key": video_key, "ContentType": ctype},
            ExpiresIn=expires_seconds,
        )
        return PresignResult(uploadUrl=upload_url, videoKey=video_key)

    def presign_thumbnail_put(
        self,
        *,
        course_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> PresignResult:
        _ = filename
        ctype = self._require_image_content_type(content_type)
        ext = _extension_for_image_content_type(ctype)
        cid = (course_id or "").strip()
        if not cid or "/" in cid:
            raise BadRequest("Invalid course id for upload")
        thumb_key = f"{cid}/thumbnail/{uuid4()}.{ext}"
        upload_url = self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket, "Key": thumb_key, "ContentType": ctype},
            ExpiresIn=expires_seconds,
        )
        return PresignResult(uploadUrl=upload_url, videoKey=thumb_key)

    def presign_lesson_thumbnail_put(
        self,
        *,
        course_id: str,
        lesson_id: str,
        filename: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> PresignResult:
        _ = filename
        ctype = self._require_image_content_type(content_type)
        ext = _extension_for_image_content_type(ctype)
        cid = (course_id or "").strip()
        lid = (lesson_id or "").strip()
        if not cid or not lid or "/" in cid or "/" in lid:
            raise BadRequest("Invalid course or lesson id for upload")
        thumb_key = f"{cid}/lessons/{lid}/thumbnail/{uuid4()}.{ext}"
        upload_url = self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket, "Key": thumb_key, "ContentType": ctype},
            ExpiresIn=expires_seconds,
        )
        return PresignResult(uploadUrl=upload_url, videoKey=thumb_key)

    def presign_get(self, *, key: str, expires_seconds: int = 3600) -> str:
        k = (key or "").strip()
        if not _is_valid_media_object_key(k):
            raise BadRequest("Invalid object key for playback")
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": k},
            ExpiresIn=expires_seconds,
        )

    def delete_object(self, key: str) -> None:
        """Delete a single object; no-op for blank keys."""
        if not key or not key.strip():
            return
        self.delete_objects([key.strip()])

    def delete_objects(self, keys: Sequence[str]) -> List[str]:
        """Delete objects by key; batches of up to 1000. Empty or duplicate keys are skipped."""
        unique = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
        if not unique:
            return []
        deleted: List[str] = []
        for i in range(0, len(unique), _S3_DELETE_BATCH):
            batch = unique[i : i + _S3_DELETE_BATCH]
            resp = self._s3.delete_objects(
                Bucket=self._bucket,
                Delete={"Objects": [{"Key": k} for k in batch], "Quiet": True},
            )
            for err in resp.get("Errors") or []:
                logger.warning(
                    "S3 delete_objects error key=%s code=%s message=%s",
                    err.get("Key"),
                    err.get("Code"),
                    err.get("Message"),
                )
            for item in resp.get("Deleted") or []:
                k = item.get("Key")
                if k:
                    deleted.append(k)
        return deleted
