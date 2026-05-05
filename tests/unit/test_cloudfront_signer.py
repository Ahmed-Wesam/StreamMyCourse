"""Unit tests for CloudFront URL signing adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from services.common.errors import BadRequest
from services.course_management.cloudfront_storage import (
    CloudFrontUrlSigner,
    rsa_sha1_sign_message,
)


def _sample_video_key() -> str:
    return (
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/lessons/"
        "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/video/"
        "cccccccc-cccc-4ccc-8ccc-cccccccccccc.mp4"
    )


@pytest.fixture
def rsa_private_pem() -> str:
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return pem.decode("utf-8")


def test_sign_url_returns_https_cloudfront_domain(rsa_private_pem: str) -> None:
    sm = MagicMock()
    sm.get_secret_value.return_value = {"SecretString": rsa_private_pem}
    signer = CloudFrontUrlSigner(
        key_pair_id="K2TESTKEYPAIR",
        secret_arn="arn:aws:secretsmanager:eu-west-1:1:secret:x",
        domain="d111111abcdef8.cloudfront.net",
        secrets_client=sm,
    )
    url = signer.sign_url(_sample_video_key(), expires_seconds=3600)
    assert url.startswith("https://d111111abcdef8.cloudfront.net/")
    assert "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" in url


def test_sign_url_includes_expires_signature_keypairid_query_params(
    rsa_private_pem: str,
) -> None:
    sm = MagicMock()
    sm.get_secret_value.return_value = {"SecretString": rsa_private_pem}
    signer = CloudFrontUrlSigner(
        key_pair_id="K2ABCDEFGHIJKL",
        secret_arn="arn:aws:secretsmanager:eu-west-1:1:secret:x",
        domain="dexample.cloudfront.net",
        secrets_client=sm,
    )
    url = signer.sign_url(_sample_video_key(), expires_seconds=7200)
    assert "Signature=" in url
    assert "Key-Pair-Id=K2ABCDEFGHIJKL" in url
    assert "Expires=" in url


def test_sign_url_uses_rsa_sha1_padding_pkcs1v15(rsa_private_pem: str) -> None:
    msg = b"hello-cloudfront-policy-bytes"
    sig = rsa_sha1_sign_message(rsa_private_pem, msg)
    priv = serialization.load_pem_private_key(
        rsa_private_pem.encode("utf-8"), password=None
    )
    pub = priv.public_key()
    pub.verify(sig, msg, padding.PKCS1v15(), hashes.SHA1())


def test_secret_loaded_once_then_cached(rsa_private_pem: str) -> None:
    sm = MagicMock()
    sm.get_secret_value.return_value = {"SecretString": rsa_private_pem}
    signer = CloudFrontUrlSigner(
        key_pair_id="K2X",
        secret_arn="arn:aws:secretsmanager:eu-west-1:1:secret:y",
        domain="dexample.cloudfront.net",
        secrets_client=sm,
    )
    k = _sample_video_key()
    signer.sign_url(k, expires_seconds=60)
    signer.sign_url(k, expires_seconds=120)
    signer.sign_url(k, expires_seconds=180)
    sm.get_secret_value.assert_called_once()


def test_invalid_object_key_rejected_before_signing(rsa_private_pem: str) -> None:
    sm = MagicMock()
    sm.get_secret_value.return_value = {"SecretString": rsa_private_pem}
    signer = CloudFrontUrlSigner(
        key_pair_id="K2X",
        secret_arn="arn:aws:secretsmanager:eu-west-1:1:secret:y",
        domain="dexample.cloudfront.net",
        secrets_client=sm,
    )
    with pytest.raises(BadRequest, match="Invalid object key"):
        signer.sign_url("../evil.mp4", expires_seconds=60)
    sm.get_secret_value.assert_not_called()
