"""Decrypt Cognito CustomEmailSender V1_0 codes (AWS Encryption SDK + KMS key)."""

from __future__ import annotations

import base64
import os
from typing import Any, Dict

import aws_encryption_sdk
from aws_encryption_sdk import CommitmentPolicy
from aws_encryption_sdk.key_providers.kms import StrictAwsKmsMasterKeyProvider


def decrypt_verification_code(
    event: Dict[str, Any],
    *,
    encryption_client: aws_encryption_sdk.EncryptionSDKClient | None = None,
    key_arn: str | None = None,
) -> str:
    """Decrypt Cognito's base64 ciphertext using the user pool KMS key."""
    request = event.get("request")
    if not isinstance(request, dict):
        raise ValueError("Missing request in custom email sender event")
    code_blob = request.get("code")
    if not isinstance(code_blob, str) or not code_blob.strip():
        raise ValueError("Missing encrypted code in request")

    kms_key_arn = (key_arn or os.environ.get("KMS_KEY_ARN") or "").strip()
    if not kms_key_arn:
        raise RuntimeError("KMS_KEY_ARN is not configured")

    client = encryption_client or aws_encryption_sdk.EncryptionSDKClient(
        commitment_policy=CommitmentPolicy.REQUIRE_ENCRYPT_ALLOW_DECRYPT,
    )
    key_provider = StrictAwsKmsMasterKeyProvider(key_ids=[kms_key_arn])
    plaintext_bytes, _header = client.decrypt(
        source=base64.b64decode(code_blob),
        key_provider=key_provider,
    )
    if not isinstance(plaintext_bytes, (bytes, bytearray)):
        raise ValueError("Encryption SDK decrypt returned no plaintext")
    return bytes(plaintext_bytes).decode("utf-8")
