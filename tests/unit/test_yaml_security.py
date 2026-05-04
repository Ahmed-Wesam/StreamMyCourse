"""Security assertions on CloudFormation templates (no wildcard S3 IAM fallback)."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_api_stack_s3_policy_no_account_wide_wildcard() -> None:
    """Lambda S3 policy must never grant Put/Get/Delete on arn:aws:s3:::* (all buckets)."""
    text = (_repo_root() / "infrastructure" / "templates" / "api-stack.yaml").read_text(encoding="utf-8")
    assert "arn:aws:s3:::*" not in text, (
        "api-stack.yaml must not use arn:aws:s3::* as S3 policy Resource when VideoBucketName is empty"
    )
    assert "streammycourse-no-bucket-configured" in text and "NEVER_MATCH" in text, (
        "expected no-bucket placeholder ARN when bucket is unset"
    )


def test_video_stack_no_cors_wildcard_and_hardening() -> None:
    text = (_repo_root() / "infrastructure" / "templates" / "video-stack.yaml").read_text(encoding="utf-8")
    assert "PublicAccessBlockConfiguration" in text
    assert "BucketEncryption" in text
    assert "SSEAlgorithm: AES256" in text
    # CORS must not allow any origin
    assert "AllowedOrigins:" in text
    assert "AllowedOrigins:\n              - '*'" not in text.replace(" ", "")
    assert "- '*'" not in text, "wildcard S3 CORS origin must not appear"
