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


def test_video_stack_https_only_and_conditional_trusted_key_groups() -> None:
    text = (_repo_root() / "infrastructure" / "templates" / "video-stack.yaml").read_text(encoding="utf-8")
    assert "ViewerProtocolPolicy: https-only" in text
    assert "TrustedKeyGroups:" in text
    assert "HasCloudFrontSigningKey" in text


def test_api_stack_cloudfront_secret_policy_uses_parameter_arn_not_star() -> None:
    text = (_repo_root() / "infrastructure" / "templates" / "api-stack.yaml").read_text(encoding="utf-8")
    assert "SecretsManagerCloudFrontSigningKey" in text
    assert "CloudFrontPrivateKeySecretArn" in text
    assert "secretsmanager:GetSecretValue" in text
    assert "HasCloudFrontSigning" in text


def test_api_stack_no_cloudfront_private_pem_parameter() -> None:
    text = (_repo_root() / "infrastructure" / "templates" / "api-stack.yaml").read_text(encoding="utf-8")
    assert "CloudFrontPrivateKeyPEM" not in text


def test_cloudfront_keys_stack_secret_only_no_embedded_private_material_param() -> None:
    text = (_repo_root() / "infrastructure" / "templates" / "cloudfront-keys-stack.yaml").read_text(
        encoding="utf-8"
    )
    assert "AWS::SecretsManager::Secret" in text
    assert "BEGIN RSA PRIVATE KEY" not in text
    assert "CloudFrontPrivateKeyPEM" not in text
