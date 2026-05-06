"""Unit tests for JWT verification edge cases and security boundaries.

Tests token expiration, invalid signatures, malformed JWTs, and claim validation.
"""

from __future__ import annotations

import base64
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from services.common.jwt_verify import (
    CognitoJwtConfig,
    VerifiedClaims,
    _decode_jwt_header,
    _decode_jwt_payload,
    _find_jwk_by_kid,
    _rsa_public_key_from_jwk,
    _validate_standard_claims,
    _verify_signature,
    verify_cognito_token,
)


SAMPLE_POOL_ID = "us-east-1_ABC123DEF"
SAMPLE_CLIENT_IDS = ["abc123def456ghi"]
SAMPLE_REGION = "us-east-1"


@pytest.fixture
def jwt_config():
    return CognitoJwtConfig(
        user_pool_id=SAMPLE_POOL_ID,
        client_ids=SAMPLE_CLIENT_IDS,
        region=SAMPLE_REGION,
    )


class TestValidateStandardClaims:
    """Tests for _validate_standard_claims edge cases."""

    def test_expired_token_fails_validation(self, jwt_config):
        """Token with past exp claim should be rejected."""
        payload = {
            "exp": time.time() - 3600,  # 1 hour ago
            "iss": jwt_config.issuer,
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "expired" in error.lower()

    def test_future_token_with_nbf_fails(self, jwt_config):
        """Token with future nbf (not before) should be rejected."""
        payload = {
            "exp": time.time() + 3600,
            "nbf": time.time() + 1800,  # 30 minutes from now
            "iss": jwt_config.issuer,
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "not yet valid" in error.lower()

    def test_invalid_exp_type_fails(self, jwt_config):
        """Token with non-numeric exp should be rejected."""
        payload = {
            "exp": "not-a-number",
            "iss": jwt_config.issuer,
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "invalid exp" in error.lower()

    def test_wrong_issuer_fails(self, jwt_config):
        """Token with wrong issuer should be rejected."""
        payload = {
            "exp": time.time() + 3600,
            "iss": "https://evil.com",
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "invalid issuer" in error.lower()

    def test_missing_issuer_fails(self, jwt_config):
        """Token without iss claim should be rejected."""
        payload = {
            "exp": time.time() + 3600,
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "invalid issuer" in error.lower()

    def test_invalid_audience_fails(self, jwt_config):
        """Token with wrong client_id in aud should be rejected."""
        payload = {
            "exp": time.time() + 3600,
            "iss": jwt_config.issuer,
            "aud": "wrong-client-id",
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "invalid audience" in error.lower()

    def test_no_client_ids_configured_with_aud_fails(self, jwt_config):
        """When no client IDs configured but aud present, should fail."""
        config_no_clients = CognitoJwtConfig(
            user_pool_id=SAMPLE_POOL_ID,
            client_ids=[],  # Empty
            region=SAMPLE_REGION,
        )
        payload = {
            "exp": time.time() + 3600,
            "iss": config_no_clients.issuer,
            "aud": "some-client",
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, config_no_clients)
        assert not is_valid
        assert "no valid client ids" in error.lower()

    def test_invalid_token_use_fails(self, jwt_config):
        """Token with invalid token_use should be rejected."""
        payload = {
            "exp": time.time() + 3600,
            "iss": jwt_config.issuer,
            "token_use": "refresh",  # Invalid
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "invalid token_use" in error.lower()

    def test_valid_token_passes(self, jwt_config):
        """Valid token should pass all checks."""
        payload = {
            "exp": time.time() + 3600,
            "iss": jwt_config.issuer,
            "aud": SAMPLE_CLIENT_IDS[0],
            "token_use": "id",
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert is_valid
        assert error == ""

    def test_optional_claims_not_required(self, jwt_config):
        """Token without optional claims (aud, token_use) can pass."""
        payload = {
            "exp": time.time() + 3600,
            "iss": jwt_config.issuer,
            "sub": "user-123",
        }
        is_valid, error = _validate_standard_claims(
            payload, jwt_config, require_client_id=False
        )
        assert is_valid
        assert error == ""


class TestDecodeJwtHeader:
    """Tests for JWT header decoding edge cases."""

    def test_malformed_jwt_wrong_segments_returns_empty(self):
        """JWT with wrong number of segments should return empty dict."""
        assert _decode_jwt_header("only.two") == {}
        assert _decode_jwt_header("only-one") == {}
        assert _decode_jwt_header("a.b.c.d") == {}

    def test_invalid_base64_in_header_returns_empty(self):
        """JWT with invalid base64 in header should return empty dict."""
        assert _decode_jwt_header("!!!.payload.signature") == {}

    def test_invalid_json_in_header_returns_empty(self):
        """JWT with invalid JSON in header should return empty dict."""
        invalid_json = base64.urlsafe_b64encode(b"not json").decode().rstrip("=")
        assert _decode_jwt_header(f"{invalid_json}.payload.signature") == {}


class TestDecodeJwtPayload:
    """Tests for JWT payload decoding edge cases."""

    def test_malformed_jwt_wrong_segments_returns_empty(self):
        """JWT with wrong number of segments should return empty dict."""
        assert _decode_jwt_payload("only.two") == {}
        assert _decode_jwt_payload("only-one") == {}

    def test_invalid_base64_in_payload_returns_empty(self):
        """JWT with invalid base64 in payload should return empty dict."""
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').decode().rstrip("=")
        assert _decode_jwt_payload(f"{header}.!!!.signature") == {}

    def test_invalid_json_in_payload_returns_empty(self):
        """JWT with invalid JSON in payload should return empty dict."""
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').decode().rstrip("=")
        invalid_json = base64.urlsafe_b64encode(b"not json").decode().rstrip("=")
        assert _decode_jwt_payload(f"{header}.{invalid_json}.signature") == {}


class TestFindJwkByKid:
    """Tests for JWK lookup edge cases."""

    def test_empty_jwks_returns_none(self):
        """Empty JWKS should return None."""
        assert _find_jwk_by_kid({"keys": []}, "kid-123") is None

    def test_missing_keys_field_returns_none(self):
        """JWKS without 'keys' field should return None."""
        assert _find_jwk_by_kid({}, "kid-123") is None

    def test_kid_not_found_returns_none(self):
        """When KID doesn't match any key, return None."""
        jwks = {"keys": [{"kid": "other"}, {"kid": "another"}]}
        assert _find_jwk_by_kid(jwks, "missing") is None


class TestRsaPublicKeyFromJwk:
    """Tests for RSA key construction edge cases."""

    def test_missing_n_parameter_raises(self):
        """JWK without 'n' parameter should raise ValueError."""
        jwk = {"e": "AQAB", "kty": "RSA"}
        with pytest.raises(ValueError, match="missing required RSA parameters"):
            _rsa_public_key_from_jwk(jwk)

    def test_missing_e_parameter_raises(self):
        """JWK without 'e' parameter should raise ValueError."""
        jwk = {"n": "some-modulus", "kty": "RSA"}
        with pytest.raises(ValueError, match="missing required RSA parameters"):
            _rsa_public_key_from_jwk(jwk)


class TestVerifySignature:
    """Tests for signature verification edge cases."""

    def test_malformed_token_returns_false(self):
        """Token with wrong segment count should return False."""
        jwk = {"kid": "test", "n": "AQAB", "e": "AQAB"}
        assert not _verify_signature("only.two.parts", jwk)

    def test_invalid_base64_signature_returns_false(self):
        """Token with invalid base64 signature should return False."""
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{}').decode().rstrip("=")
        jwk = {"kid": "test", "n": "AQAB", "e": "AQAB"}
        assert not _verify_signature(f"{header}.{payload}.!!!", jwk)


class TestVerifyCognitoToken:
    """Integration-style tests for verify_cognito_token."""

    def test_none_config_returns_none(self):
        """When config is None, should return None."""
        assert verify_cognito_token("token", None) is None

    def test_empty_config_returns_none(self):
        """When config has empty pool_id/region, should return None."""
        config = CognitoJwtConfig(user_pool_id="", client_ids=[], region="")
        assert verify_cognito_token("token", config) is None

    def test_malformed_token_returns_none(self):
        """Token without 3 segments should return None."""
        config = CognitoJwtConfig(
            user_pool_id=SAMPLE_POOL_ID,
            client_ids=SAMPLE_CLIENT_IDS,
            region=SAMPLE_REGION,
        )
        assert verify_cognito_token("not.enough", config) is None
        assert verify_cognito_token("too.many.segments.here", config) is None

    def test_token_without_kid_returns_none(self, jwt_config):
        """Token without kid in header should return None."""
        # Create token without kid
        header = base64.urlsafe_b64encode(b'{"alg":"RS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            json.dumps({
                "sub": "user-123",
                "exp": time.time() + 3600,
                "iss": jwt_config.issuer,
            }).encode()
        ).decode().rstrip("=")
        token = f"{header}.{payload}.signature"
        assert verify_cognito_token(token, jwt_config) is None

    def test_jwks_fetch_failure_returns_none(self, jwt_config):
        """When JWKS fetch fails and no cache, should return None."""
        header = base64.urlsafe_b64encode(
            b'{"alg":"RS256","kid":"test-kid"}'
        ).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(
            json.dumps({
                "sub": "user-123",
                "exp": time.time() + 3600,
                "iss": jwt_config.issuer,
            }).encode()
        ).decode().rstrip("=")
        token = f"{header}.{payload}.signature"

        with patch(
            "services.common.jwt_verify._fetch_jwks",
            side_effect=Exception("network error"),
        ):
            assert verify_cognito_token(token, jwt_config) is None
