"""Shared S3 object key validation for lesson media (video + thumbnails).

Extracted so CloudFront signing and S3 presign paths share one definition without
import cycles between ``storage`` and ``cloudfront_storage``.
"""

from __future__ import annotations

import re

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


def is_valid_media_object_key(key: str) -> bool:
    k = (key or "").strip()
    if not k or ".." in k or "//" in k or k.startswith("/"):
        return False
    return any(p.fullmatch(k) is not None for p in _MEDIA_KEY_PATTERNS)
