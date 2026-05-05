"""Unit tests for JWT verification module.

Tests Cognito JWT signature verification, JWKS caching, and claim validation.
"""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

# Import the module under test
from config import _parse_cognito_pool_arn
from services.common.jwt_verify import (
    CognitoJwtConfig,
    VerifiedClaims,
    _base64url_decode,
    _clear_jwks_cache_for_tests,
    _decode_jwt_header,
    _decode_jwt_payload,
    _find_jwk_by_kid,
    _validate_standard_claims,
    parse_jwt_claims_verified,
    verify_cognito_token,
)


# Sample test data
SAMPLE_POOL_ID = "us-east-1_ABC123DEF"
SAMPLE_CLIENT_IDS = ["abc123def456ghi", "xyz789uvw456rst"]
SAMPLE_REGION = "us-east-1"


@pytest.fixture
def jwt_config():
    """Create a test JWT config."""
    return CognitoJwtConfig(
        user_pool_id=SAMPLE_POOL_ID,
        client_ids=SAMPLE_CLIENT_IDS,
        region=SAMPLE_REGION,
    )


@pytest.fixture(autouse=True)
def clear_jwks_cache():
    """Clear JWKS cache before each test."""
    _clear_jwks_cache_for_tests()
    yield
    _clear_jwks_cache_for_tests()


class TestCognitoJwtConfig:
    """Tests for CognitoJwtConfig dataclass."""

    def test_issuer_property(self, jwt_config):
        """Test that issuer is correctly formatted."""
        expected_issuer = f"https://cognito-idp.{SAMPLE_REGION}.amazonaws.com/{SAMPLE_POOL_ID}"
        assert jwt_config.issuer == expected_issuer

    def test_jwks_url_property(self, jwt_config):
        """Test that JWKS URL is correctly formatted."""
        expected_url = (
            f"https://cognito-idp.{SAMPLE_REGION}.amazonaws.com/{SAMPLE_POOL_ID}/.well-known/jwks.json"
        )
        assert jwt_config.jwks_url == expected_url

    def test_client_ids_list(self, jwt_config):
        """Test that client_ids is a list."""
        assert isinstance(jwt_config.client_ids, list)
        assert len(jwt_config.client_ids) == 2
        assert "abc123def456ghi" in jwt_config.client_ids
        assert "xyz789uvw456rst" in jwt_config.client_ids


class TestBase64UrlDecode:
    """Tests for base64url decoding."""

    def test_decode_with_padding(self):
        """Test decoding with proper padding."""
        # "hello" -> base64url -> "aGVsbG8"
        encoded = "aGVsbG8"
        result = _base64url_decode(encoded)
        assert result == b"hello"

    def test_decode_without_padding(self):
        """Test decoding without padding (padding added automatically)."""
        # "hello world" -> base64url -> "aGVsbG8gd29ybGQ"
        encoded = "aGVsbG8gd29ybGQ"
        result = _base64url_decode(encoded)
        assert result == b"hello world"

    def test_decode_with_existing_padding(self):
        """Test decoding when padding already exists."""
        # "test" -> base64url -> "dGVzdA=="
        encoded = "dGVzdA=="
        result = _base64url_decode(encoded)
        assert result == b"test"


class TestDecodeJwtHeader:
    """Tests for JWT header decoding."""

    def test_valid_header(self):
        """Test decoding a valid JWT header."""
        # Create a valid JWT header with kid
        header = {"alg": "RS256", "kid": "test-key-id", "typ": "JWT"}
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        )
        payload_b64 = "e30"  # {}
        signature_b64 = "c2ln"  # "sig"
        token = f"{header_b64}.{payload_b64}.{signature_b64}"

        result = _decode_jwt_header(token)
        assert result["kid"] == "test-key-id"
        assert result["alg"] == "RS256"

    def test_invalid_token_format(self):
        """Test handling invalid token format."""
        assert _decode_jwt_header("invalid.token") == {}
        assert _decode_jwt_header("only_one_part") == {}
        assert _decode_jwt_header("") == {}


class TestDecodeJwtPayload:
    """Tests for JWT payload decoding."""

    def test_valid_payload(self):
        """Test decoding a valid JWT payload."""
        payload = {"sub": "user123", "email": "test@example.com"}
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )
        header_b64 = "eyJhbGciOiJSUzI1NiJ9"  # {"alg":"RS256"}
        signature_b64 = "c2ln"
        token = f"{header_b64}.{payload_b64}.{signature_b64}"

        result = _decode_jwt_payload(token)
        assert result["sub"] == "user123"
        assert result["email"] == "test@example.com"

    def test_invalid_payload(self):
        """Test handling invalid payload."""
        assert _decode_jwt_payload("invalid.token.here") == {}


class TestFindJwkByKid:
    """Tests for finding JWK by key ID."""

    def test_find_existing_key(self):
        """Test finding a key that exists."""
        jwks = {
            "keys": [
                {"kid": "key1", "kty": "RSA"},
                {"kid": "key2", "kty": "RSA"},
            ]
        }
        result = _find_jwk_by_kid(jwks, "key2")
        assert result == {"kid": "key2", "kty": "RSA"}

    def test_find_nonexistent_key(self):
        """Test finding a key that doesn't exist."""
        jwks = {"keys": [{"kid": "key1", "kty": "RSA"}]}
        result = _find_jwk_by_kid(jwks, "nonexistent")
        assert result is None

    def test_empty_jwks(self):
        """Test with empty JWKS."""
        assert _find_jwk_by_kid({}, "key1") is None
        assert _find_jwk_by_kid({"keys": []}, "key1") is None


class TestValidateStandardClaims:
    """Tests for standard JWT claim validation."""

    def test_valid_token(self, jwt_config):
        """Test validation with valid claims."""
        import time

        now = time.time()
        payload = {
            "sub": "user123",
            "iss": jwt_config.issuer,
            "aud": jwt_config.client_ids[0],
            "exp": now + 3600,
            "token_use": "id",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert is_valid
        assert error == ""

    def test_expired_token(self, jwt_config):
        """Test validation with expired token."""
        import time

        now = time.time()
        payload = {
            "sub": "user123",
            "iss": jwt_config.issuer,
            "aud": jwt_config.client_ids[0],
            "exp": now - 3600,  # 1 hour ago
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "expired" in error.lower()

    def test_invalid_issuer(self, jwt_config):
        """Test validation with wrong issuer."""
        payload = {
            "sub": "user123",
            "iss": "https://malicious-issuer.com",
            "aud": jwt_config.client_ids[0],
            "exp": 9999999999,
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "issuer" in error.lower() or "invalid" in error.lower()

    def test_invalid_audience(self, jwt_config):
        """Test validation with wrong audience."""
        import time

        now = time.time()
        payload = {
            "sub": "user123",
            "iss": jwt_config.issuer,
            "aud": "wrong-client-id",
            "exp": now + 3600,
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "audience" in error.lower() or "invalid" in error.lower()

    def test_second_client_id_valid(self, jwt_config):
        """Test that second client ID in list is accepted."""
        import time

        now = time.time()
        payload = {
            "sub": "user123",
            "iss": jwt_config.issuer,
            "aud": jwt_config.client_ids[1],  # Second client ID
            "exp": now + 3600,
            "token_use": "id",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert is_valid
        assert error == ""

    def test_not_before_token(self, jwt_config):
        """Test validation with nbf in the future."""
        import time

        now = time.time()
        payload = {
            "sub": "user123",
            "iss": jwt_config.issuer,
            "aud": jwt_config.client_ids[0],
            "exp": now + 3600,
            "nbf": now + 1800,  # Valid 30 minutes from now
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "not yet valid" in error.lower()

    def test_invalid_token_use(self, jwt_config):
        """Test validation with invalid token_use."""
        import time

        now = time.time()
        payload = {
            "sub": "user123",
            "iss": jwt_config.issuer,
            "aud": jwt_config.client_ids[0],
            "exp": now + 3600,
            "token_use": "invalid",
        }
        is_valid, error = _validate_standard_claims(payload, jwt_config)
        assert not is_valid
        assert "token_use" in error.lower()


class TestVerifyCognitoToken:
    """Tests for the main verify_cognito_token function."""

    def test_no_config_returns_none(self):
        """Test that None config returns None."""
        result = verify_cognito_token("some.token.here", None)
        assert result is None

    def test_invalid_token_format(self, jwt_config):
        """Test handling invalid token format."""
        assert verify_cognito_token("invalid", jwt_config) is None
        assert verify_cognito_token("only.two.parts", jwt_config) is None

    def test_missing_kid(self, jwt_config):
        """Test handling token without kid in header."""
        # Create token without kid
        header = {"alg": "RS256"}
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        )
        payload_b64 = "e30"
        signature_b64 = "c2ln"
        token = f"{header_b64}.{payload_b64}.{signature_b64}"

        result = verify_cognito_token(token, jwt_config)
        assert result is None


class TestParseJwtClaimsVerified:
    """Tests for parse_jwt_claims_verified function."""

    def test_no_config_returns_empty_dict(self):
        """Test that None config returns empty dict."""
        result = parse_jwt_claims_verified("some.token.here", None)
        assert result == {}

    def test_invalid_token_returns_empty_dict(self, jwt_config):
        """Test that invalid token returns empty dict (fail-secure)."""
        result = parse_jwt_claims_verified("invalid", jwt_config)
        assert result == {}


class TestParseCognitoPoolArn:
    """Tests for _parse_cognito_pool_arn helper."""

    def test_valid_arn(self):
        """Test parsing a valid Cognito User Pool ARN."""
        arn = "arn:aws:cognito-idp:us-east-1:123456789012:userpool/us-east-1_ABC123DEF"
        region, pool_id = _parse_cognito_pool_arn(arn)
        assert region == "us-east-1"
        assert pool_id == "us-east-1_ABC123DEF"

    def test_empty_arn(self):
        """Test parsing empty ARN."""
        region, pool_id = _parse_cognito_pool_arn("")
        assert region == ""
        assert pool_id == ""

    def test_invalid_arn(self):
        """Test parsing invalid ARN formats."""
        # No userpool part
        region, pool_id = _parse_cognito_pool_arn("arn:aws:cognito-idp:us-east-1:123456789012")
        assert region == ""
        assert pool_id == ""

        # Wrong service
        region, pool_id = _parse_cognito_pool_arn("arn:aws:s3:::bucket-name")
        assert region == ""
        assert pool_id == ""

    def test_whitespace_arn(self):
        """Test parsing ARN with whitespace."""
        arn = "  arn:aws:cognito-idp:us-west-2:123456789012:userpool/us-west-2_XYZ789  "
        region, pool_id = _parse_cognito_pool_arn(arn)
        assert region == "us-west-2"
        assert pool_id == "us-west-2_XYZ789"


class TestVerifiedClaims:
    """Tests for VerifiedClaims dataclass."""

    def test_basic_claims(self):
        """Test creating VerifiedClaims with basic fields."""
        claims = VerifiedClaims(
            sub="user123",
            role="teacher",
            email="test@example.com",
        )
        assert claims.sub == "user123"
        assert claims.role == "teacher"
        assert claims.email == "test@example.com"
        assert claims.claims == {}

    def test_with_claims_dict(self):
        """Test creating VerifiedClaims with custom claims dict."""
        extra_claims = {"custom:org": "acme", "cognito:username": "johndoe"}
        claims = VerifiedClaims(
            sub="user123",
            role="student",
            claims=extra_claims,
        )
        assert claims.sub == "user123"
        assert claims.claims["custom:org"] == "acme"


class TestIntegrationFlow:
    """Integration-style tests for the complete verification flow."""

    @patch("services.common.jwt_verify._fetch_jwks")
    def test_successful_verification_flow(self, mock_fetch, jwt_config):
        """Test the complete verification flow with mocked JWKS."""
        import time

        # This is a complex test that would require generating real RSA keys
        # For unit tests, we mock the signature verification
        # Real signature verification tests should be in integration tests

        now = time.time()
        payload = {
            "sub": "user123",
            "custom:role": "teacher",
            "email": "teacher@example.com",
            "iss": jwt_config.issuer,
            "aud": jwt_config.client_ids[0],
            "exp": now + 3600,
            "token_use": "id",
        }

        # Create a mock token (signature will fail, but we test the flow)
        header = {"alg": "RS256", "kid": "test-key"}
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        )
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )
        token = f"{header_b64}.{payload_b64}.invalid_sig"

        # Mock JWKS with a fake key
        mock_fetch.return_value = {
            "keys": [
                {
                    "kid": "test-key",
                    "kty": "RSA",
                    "n": "xGOrOgVWfB8N8",
                    "e": "AQAB",
                }
            ]
        }

        # Since we can't verify the signature without real keys,
        # this will fail at signature verification
        result = verify_cognito_token(token, jwt_config)
        # With an invalid signature, result should be None
        assert result is None

    @patch("services.common.jwt_verify._fetch_jwks")
    def test_apigw_claims_format(self, mock_fetch_jwks, jwt_config):
        """Test that parse_jwt_claims_verified returns API Gateway compatible format."""
        import time

        # Mock the JWKS response
        mock_fetch_jwks.return_value = {
            "keys": [
                {
                    "kid": "test-key",
                    "kty": "RSA",
                    "n": "xGOrOgVWfB8N8",
                    "e": "AQAB",
                }
            ]
        }

        now = time.time()
        payload = {
            "sub": "user123",
            "custom:role": "teacher",
            "email": "teacher@example.com",
            "iss": jwt_config.issuer,
            "aud": jwt_config.client_ids[0],
            "exp": now + 3600,
            "token_use": "id",
            "cognito:username": "johndoe",
        }

        header = {"alg": "RS256", "kid": "test-key"}
        header_b64 = (
            base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        )
        payload_b64 = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )
        token = f"{header_b64}.{payload_b64}.invalid_sig"

        # Mock the verification to return the claims
        with patch(
            "services.common.jwt_verify._verify_signature",
            return_value=True,
        ):
            result = parse_jwt_claims_verified(token, jwt_config)

            # Should return claims in API Gateway authorizer format
            assert result["sub"] == "user123"
            assert result["custom:role"] == "teacher"
            assert result["email"] == "teacher@example.com"
            assert result["iss"] == jwt_config.issuer
            assert result["aud"] == jwt_config.client_ids[0]
            assert result["token_use"] == "id"
            assert result["cognito:username"] == "johndoe"
