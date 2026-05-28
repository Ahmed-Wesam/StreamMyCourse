from __future__ import annotations

import os
import re

try:
    import boto3
    from botocore.config import Config
except Exception:  # pragma: no cover
    boto3 = None
    Config = None  # type: ignore[misc, assignment]

from services.common.errors import BadRequest

S3_DELETE_BATCH = 1000

MAX_VIDEO_UPLOAD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GiB (documented; S3 single PUT max 5 GiB)

ALLOWED_VIDEO_CONTENT_TYPES = frozenset(
    {"video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"}
)
ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
)

_UUID_SEGMENT = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

_VIDEO_KEY_PATTERN = re.compile(
    rf"^({_UUID_SEGMENT})/lessons/({_UUID_SEGMENT})/video/({_UUID_SEGMENT})\.(mp4|webm|mov|avi)$"
)
_LESSON_THUMBNAIL_KEY_PATTERN = re.compile(
    rf"^({_UUID_SEGMENT})/lessons/({_UUID_SEGMENT})/thumbnail/({_UUID_SEGMENT})\.(jpg|png|webp|gif)$"
)
_COURSE_THUMBNAIL_KEY_PATTERN = re.compile(
    rf"^({_UUID_SEGMENT})/thumbnail/({_UUID_SEGMENT})\.(jpg|png|webp|gif)$"
)

_MEDIA_KEY_PATTERNS = (
    _VIDEO_KEY_PATTERN,
    _LESSON_THUMBNAIL_KEY_PATTERN,
    _COURSE_THUMBNAIL_KEY_PATTERN,
)
_IMAGE_KEY_PATTERNS = (_LESSON_THUMBNAIL_KEY_PATTERN, _COURSE_THUMBNAIL_KEY_PATTERN)


def normalize_content_type(raw: str) -> str:
    t = (raw or "").strip().lower()
    if not t:
        return ""
    return t.split(";", 1)[0].strip()


def extension_for_video_content_type(norm: str) -> str:
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


def extension_for_image_content_type(norm: str) -> str:
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


def is_valid_media_object_key(key: str) -> bool:
    k = (key or "").strip()
    if not k or ".." in k or "//" in k or k.startswith("/"):
        return False
    return any(p.fullmatch(k) is not None for p in _MEDIA_KEY_PATTERNS)


def is_valid_video_object_key(key: str) -> bool:
    k = (key or "").strip()
    if not k or ".." in k or "//" in k or k.startswith("/"):
        return False
    return _VIDEO_KEY_PATTERN.fullmatch(k) is not None


def is_valid_image_object_key(key: str) -> bool:
    k = (key or "").strip()
    if not k or ".." in k or "//" in k or k.startswith("/"):
        return False
    return any(p.fullmatch(k) is not None for p in _IMAGE_KEY_PATTERNS)


def s3_client():
    """Regional SigV4 client so presigned URLs use bucket.s3.<region>.amazonaws.com (not global SigV2)."""
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
