from __future__ import annotations

from pathlib import Path

_API_STACK = (
    Path(__file__).resolve().parents[2]
    / "infrastructure"
    / "templates"
    / "api-stack.yaml"
)


def test_catalog_lambda_role_can_get_lesson_video_objects_for_presigned_playback() -> None:
    """Presigned playback URLs are signed by the catalog role; S3 denies GET without GetObject."""
    text = _API_STACK.read_text(encoding="utf-8")
    assert "PolicyName: S3PresignedUrl" in text
    assert "s3:GetObject" in text
    assert "${VideoBucketName}/*/lessons/*/video/*" in text
