"""CloudFront signed URL generation and cache invalidation for lesson media.

CloudFront URL signing uses RSA-SHA1 per AWS CloudFront API requirements (PKCS#1 v1.5
padding over SHA-1); this is protocol-defined, not a standalone cryptographic choice.

Secrets Manager holds the PEM-encoded RSA **private** key; the matching **public** key
is registered on the CloudFront distribution via a key group.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Sequence

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore[misc, assignment]

from botocore.signers import CloudFrontSigner
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from services.common.errors import BadRequest
from services.course_management.media_keys import is_valid_media_object_key

logger = logging.getLogger(__name__)


def rsa_sha1_sign_message(private_key_pem: str, message: bytes) -> bytes:
    """Sign ``message`` with RSA PKCS#1 v1.5 + SHA-1 (CloudFront canned policy)."""
    key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
    )
    return key.sign(message, padding.PKCS1v15(), hashes.SHA1())


def _rsa_signer(private_key_pem: str) -> Callable[[bytes], bytes]:
    return lambda msg: rsa_sha1_sign_message(private_key_pem, msg)


class CloudFrontUrlSigner:
    """Generates time-limited signed HTTPS URLs for objects behind CloudFront."""

    def __init__(
        self,
        *,
        key_pair_id: str,
        secret_arn: str,
        domain: str,
        secrets_client: Any | None = None,
    ) -> None:
        self._key_pair_id = (key_pair_id or "").strip()
        self._secret_arn = (secret_arn or "").strip()
        self._domain = (domain or "").strip().lower().rstrip("/")
        if boto3 is None:
            raise RuntimeError("boto3 is not available")
        self._secrets = secrets_client or boto3.client("secretsmanager")
        self._signer: CloudFrontSigner | None = None

    def _get_signer(self) -> CloudFrontSigner:
        if self._signer is None:
            resp = self._secrets.get_secret_value(SecretId=self._secret_arn)
            pem = str(resp.get("SecretString") or "")
            if not pem.strip():
                raise RuntimeError("CloudFront private key secret is empty")
            self._signer = CloudFrontSigner(self._key_pair_id, _rsa_signer(pem))
        return self._signer

    def sign_url(self, key: str, *, expires_seconds: int) -> str:
        k = (key or "").strip()
        if not is_valid_media_object_key(k):
            raise BadRequest("Invalid object key for playback")
        if expires_seconds <= 0:
            raise BadRequest("expires_seconds must be positive")
        url = f"https://{self._domain}/{k}"
        date_less_than = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
        return self._get_signer().generate_presigned_url(url, date_less_than=date_less_than)


class CloudFrontInvalidator:
    """Fire-and-forget invalidation via the video stack's invoke-only Lambda."""

    def __init__(self, *, function_name: str, lambda_client: Any | None = None) -> None:
        self._fn = (function_name or "").strip()
        if boto3 is None:
            raise RuntimeError("boto3 is not available")
        self._lambda = lambda_client or boto3.client("lambda")

    def invalidate_paths(self, keys_or_paths: Sequence[str]) -> None:
        """Normalize S3 keys or paths starting with ``/`` and invoke invalidation Lambda."""
        if not self._fn:
            return
        paths: List[str] = []
        for raw in keys_or_paths:
            s = (raw or "").strip()
            if not s:
                continue
            paths.append(s if s.startswith("/") else f"/{s}")
        if not paths:
            return
        try:
            self._lambda.invoke(
                FunctionName=self._fn,
                InvocationType="Event",
                Payload=json.dumps({"paths": paths}).encode("utf-8"),
            )
        except Exception as exc:  # pragma: no cover - network / IAM edge paths
            logger.warning("CloudFront invalidation invoke failed: %s", exc)
