"""Decrypt Cognito CustomEmailSender V1_0 codes with KMS."""

from __future__ import annotations

import base64
from typing import Any, Dict

import boto3


def decrypt_verification_code(event: Dict[str, Any], *, kms_client: Any | None = None) -> str:
    request = event.get("request")
    if not isinstance(request, dict):
        raise ValueError("Missing request in custom email sender event")
    code_blob = request.get("code")
    if not isinstance(code_blob, str) or not code_blob.strip():
        raise ValueError("Missing encrypted code in request")

    user_pool_id = str(event.get("userPoolId") or "").strip()
    caller = event.get("callerContext") if isinstance(event.get("callerContext"), dict) else {}
    client_id = str(caller.get("clientId") or "").strip()
    trigger_source = str(event.get("triggerSource") or "").strip()

    encryption_context: Dict[str, str] = {"userpool-id": user_pool_id}
    if client_id:
        encryption_context["client-id"] = client_id
    if trigger_source:
        encryption_context["trigger-source"] = trigger_source

    kms = kms_client or boto3.client("kms")
    decrypted = kms.decrypt(
        CiphertextBlob=base64.b64decode(code_blob),
        EncryptionContext=encryption_context,
    )
    plaintext = decrypted.get("Plaintext")
    if not isinstance(plaintext, (bytes, bytearray)):
        raise ValueError("KMS decrypt returned no plaintext")
    return bytes(plaintext).decode("utf-8")
