from __future__ import annotations

import logging
from typing import List, Sequence
from uuid import uuid4

from services.common.errors import BadRequest
from services.course_management.models import LessonFilePresignResult, PresignResult
from services.course_management.s3_common import (
    ALLOWED_VIDEO_CONTENT_TYPES,
    S3_DELETE_BATCH,
    content_type_for_lesson_file_type,
    extension_for_lesson_file_type,
    extension_for_video_content_type,
    is_valid_lesson_file_object_key,
    is_valid_video_object_key,
    lesson_file_object_key,
    normalize_content_type,
    sanitize_download_filename,
    s3_client as _s3_client,
)

logger = logging.getLogger(__name__)


class CourseMediaStorage:
    """S3 presign/delete adapter for lesson video objects (Slice 1: video-only)."""

    def __init__(self, video_bucket: str):
        if not video_bucket:
            raise RuntimeError("VIDEO_BUCKET is required for uploads")
        self._bucket = video_bucket
        self._s3 = _s3_client()

    @staticmethod
    def _require_video_content_type(content_type: str) -> str:
        norm = normalize_content_type(content_type)
        if norm not in ALLOWED_VIDEO_CONTENT_TYPES:
            raise BadRequest("Invalid or unsupported video content type")
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
        _ = filename
        ctype = self._require_video_content_type(content_type)
        ext = extension_for_video_content_type(ctype)
        cid = (course_id or "").strip()
        lid = (lesson_id or "").strip()
        if not cid or not lid or "/" in cid or "/" in lid:
            raise BadRequest("Invalid course or lesson id for upload")
        video_key = f"{cid}/lessons/{lid}/video/{uuid4()}.{ext}"
        upload_url = self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket, "Key": video_key, "ContentType": ctype},
            ExpiresIn=expires_seconds,
        )
        return PresignResult(uploadUrl=upload_url, videoKey=video_key)

    def presign_get(self, *, key: str, expires_seconds: int = 3600) -> str:
        k = (key or "").strip()
        if not is_valid_video_object_key(k):
            raise BadRequest("Invalid object key for playback")
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": k},
            ExpiresIn=expires_seconds,
        )

    def delete_object(self, key: str) -> None:
        if not key or not key.strip():
            return
        self.delete_objects([key.strip()])

    def delete_objects(self, keys: Sequence[str]) -> List[str]:
        unique = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
        if not unique:
            return []
        deleted: List[str] = []
        for i in range(0, len(unique), S3_DELETE_BATCH):
            batch = unique[i : i + S3_DELETE_BATCH]
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


class LessonFileStorage:
    """S3 presign/HEAD adapter for lesson attachment objects."""

    def __init__(self, video_bucket: str):
        if not video_bucket:
            raise RuntimeError("VIDEO_BUCKET is required for lesson file uploads")
        self._bucket = video_bucket
        self._s3 = _s3_client()

    def presign_put_file(
        self,
        *,
        course_id: str,
        lesson_id: str,
        file_id: str,
        file_type: str,
        byte_size: int,
        expires_seconds: int = 300,
    ) -> LessonFilePresignResult:
        if byte_size <= 0:
            raise BadRequest("byte_size must be positive")
        ctype = content_type_for_lesson_file_type(file_type)
        _ = extension_for_lesson_file_type(file_type)
        object_key = lesson_file_object_key(
            course_id=course_id,
            lesson_id=lesson_id,
            file_id=file_id,
            file_type=file_type,
        )
        upload_url = self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self._bucket,
                "Key": object_key,
                "ContentType": ctype,
                "ContentLength": int(byte_size),
            },
            ExpiresIn=expires_seconds,
        )
        return LessonFilePresignResult(uploadUrl=upload_url, objectKey=object_key)

    def head_object(self, key: str) -> dict:
        k = (key or "").strip()
        if not is_valid_lesson_file_object_key(k):
            raise BadRequest("Invalid lesson file object key")
        try:
            return self._s3.head_object(Bucket=self._bucket, Key=k)
        except Exception as exc:
            response = getattr(exc, "response", None)
            if isinstance(response, dict):
                code = (response.get("Error") or {}).get("Code")
                if code in ("404", "NoSuchKey", "NotFound"):
                    raise BadRequest("Uploaded file not found in storage") from exc
            raise

    def delete_object(self, key: str) -> None:
        k = (key or "").strip()
        if not k or not is_valid_lesson_file_object_key(k):
            return
        self._s3.delete_object(Bucket=self._bucket, Key=k)

    def presign_get_file(
        self,
        *,
        key: str,
        kind: str,
        title: str,
        file_type: str,
        expires_seconds: int = 300,
    ) -> str:
        k = (key or "").strip()
        if not is_valid_lesson_file_object_key(k):
            raise BadRequest("Invalid lesson file object key")
        ext = extension_for_lesson_file_type(file_type)
        safe_name = sanitize_download_filename(title)
        disposition_type = "inline"
        if (kind or "").strip().lower() != "resource" or ext != "pdf":
            disposition_type = "attachment"
        disposition = f'{disposition_type}; filename="{safe_name}.{ext}"'
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self._bucket,
                "Key": k,
                "ResponseContentDisposition": disposition,
            },
            ExpiresIn=expires_seconds,
        )
