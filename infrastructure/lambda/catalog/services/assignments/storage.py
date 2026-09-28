"""S3 adapter for assignment file and image objects (RS-13)."""

from __future__ import annotations

import os
from typing import Optional

try:
    import boto3
    from botocore.config import Config
except Exception:  # pragma: no cover
    boto3 = None
    Config = None  # type: ignore[misc, assignment]

from services.assignments.ports import ObjectHead


def _sanitize_download_filename(title: str) -> str:
    """Strip characters unsafe in Content-Disposition filenames; cap length."""
    cleaned = (title or "").strip()
    for ch in ("\r", "\n", '"', ";", "\\"):
        cleaned = cleaned.replace(ch, "")
    if len(cleaned) > 120:
        cleaned = cleaned[:120]
    return cleaned or "download"


def _s3_client():
    """Regional SigV4 client so presigned URLs use virtual-hosted style."""
    if boto3 is None or Config is None:
        raise RuntimeError("boto3 is not available")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "eu-west-1"
    cfg = Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"},
        connect_timeout=5,
        read_timeout=15,
    )
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://s3.{region}.amazonaws.com",
        config=cfg,
    )


class AssignmentFileStorage:
    """S3 presign/HEAD/delete adapter matching AssignmentStoragePort."""

    def __init__(self, video_bucket: str):
        if not video_bucket:
            raise RuntimeError("VIDEO_BUCKET is required for assignment uploads")
        self._bucket = video_bucket
        self._s3 = _s3_client()

    def _require_key(self, key: str) -> str:
        k = (key or "").strip()
        if not k:
            raise ValueError("object key is required")
        return k

    def presign_put(self, key: str, content_type: str, content_length: int) -> str:
        k = self._require_key(key)
        return self._s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": self._bucket,
                "Key": k,
                "ContentType": content_type,
                "ContentLength": int(content_length),
            },
            ExpiresIn=300,
        )

    def head(self, key: str) -> Optional[ObjectHead]:
        k = self._require_key(key)
        try:
            resp = self._s3.head_object(Bucket=self._bucket, Key=k)
        except Exception as exc:
            response = getattr(exc, "response", None)
            if isinstance(response, dict):
                code = (response.get("Error") or {}).get("Code")
                if code in ("404", "NoSuchKey", "NotFound"):
                    return None
            raise
        content_type = str(resp.get("ContentType") or "")
        content_length = int(resp.get("ContentLength") or 0)
        return ObjectHead(content_type=content_type, content_length=content_length)

    def delete(self, key: str) -> None:
        k = self._require_key(key)
        self._s3.delete_object(Bucket=self._bucket, Key=k)

    def presign_get(
        self,
        key: str,
        *,
        disposition: str,
        download_filename: str,
        expires_seconds: int,
    ) -> str:
        k = self._require_key(key)
        safe_name = _sanitize_download_filename(download_filename)
        content_disposition = f'{disposition}; filename="{safe_name}"'
        return self._s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": self._bucket,
                "Key": k,
                "ResponseContentDisposition": content_disposition,
            },
            ExpiresIn=int(expires_seconds),
        )
