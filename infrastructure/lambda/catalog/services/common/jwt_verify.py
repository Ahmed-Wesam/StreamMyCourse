"""JWT signature verification for Cognito tokens.

Provides JWKS fetching/caching and RSA signature verification for JWTs
issued by Amazon Cognito. Validates exp, iss, aud, and token_use claims.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Module-level JWKS cache to avoid fetching on every request in warm containers
_jwks_cache: Dict[str, Any] = {}
_jwks_cache_expiry: float = 0.0
_JWKS_CACHE_TTL_SECONDS = 3600  # 1 hour


@dataclass(frozen=True)
class CognitoJwtConfig:
    """Configuration for Cognito JWT verification."""

    user_pool_id: str
    client_ids: List[str]  # App client IDs for audience validation (supports multiple)
    region: str

    @property
    def issuer(self) -> str:
        """Cognito ID token issuer (iss claim)."""
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_url(self) -> str:
        """JWKS endpoint URL."""
        return f"{self.issuer}/.well-known/jwks.json"


@dataclass(frozen=True)
class VerifiedClaims:
    """Verified JWT claims after signature and standard claim validation."""

    sub: str  # Cognito user subject (UUID)
    role: str  # custom:role claim
    email: Optional[str] = None
    claims: Dict[str, Any] = None  # All claims

    def __post_init__(self) -> None:
        if self.claims is None:
            object.__setattr__(self, "claims", {})


def _fetch_jwks(jwks_url: str) -> Dict[str, Any]:
    """Fetch JWKS from Cognito public endpoint.

    Raises:
        urllib.error.URLError: If the request fails.
        json.JSONDecodeError: If the response is not valid JSON.
    """
    req = urllib.request.Request(
        jwks_url,
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_cached_jwks(config: CognitoJwtConfig) -> Dict[str, Any]:
    """Get JWKS with in-memory caching per container (Lambda warm start)."""
    global _jwks_cache, _jwks_cache_expiry

    now = time.time()
    cache_key = config.user_pool_id

    if _jwks_cache.get(cache_key) and now < _jwks_cache_expiry:
        return _jwks_cache[cache_key]

    try:
        jwks = _fetch_jwks(config.jwks_url)
        _jwks_cache[cache_key] = jwks
        _jwks_cache_expiry = now + _JWKS_CACHE_TTL_SECONDS
        return jwks
    except Exception as exc:
        logger.warning("Failed to fetch JWKS from %s: %s", config.jwks_url, exc)
        # Return stale cache if available, otherwise empty
        return _jwks_cache.get(cache_key, {})


def _base64url_decode(b64url: str) -> bytes:
    """Decode base64url string with padding fix."""
    padding_needed = 4 - len(b64url) % 4
    if padding_needed != 4:
        b64url += "=" * padding_needed
    # Use standard library base64
    import base64

    return base64.urlsafe_b64decode(b64url)


def _decode_jwt_header(token: str) -> Dict[str, Any]:
    """Decode JWT header to get the key ID (kid)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        header_bytes = _base64url_decode(parts[0])
        return json.loads(header_bytes.decode("utf-8"))
    except Exception:
        return {}


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    """Decode JWT payload (claims) without verification."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_bytes = _base64url_decode(parts[1])
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return {}


def _rsa_public_key_from_jwk(jwk: Dict[str, str]) -> Any:
    """Construct an RSA public key from a JWK dict.

    Uses cryptography library if available, otherwise raises.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError as exc:
        raise RuntimeError(
            "cryptography library is required for JWT signature verification"
        ) from exc

    # JWK RSA parameters
    n_b64 = jwk.get("n", "")
    e_b64 = jwk.get("e", "")

    if not n_b64 or not e_b64:
        raise ValueError("JWK missing required RSA parameters (n, e)")

    n_bytes = _base64url_decode(n_b64)
    e_bytes = _base64url_decode(e_b64)

    # Convert bytes to integers
    n = int.from_bytes(n_bytes, byteorder="big")
    e = int.from_bytes(e_bytes, byteorder="big")

    # Construct RSA public key
    public_numbers = rsa.RSAPublicNumbers(e=e, n=n)
    return public_numbers.public_key()


def _verify_signature(token: str, jwk: Dict[str, str]) -> bool:
    """Verify JWT signature using the provided JWK.

    Returns True if signature is valid, False otherwise.
    """
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        parts = token.split(".")
        if len(parts) != 3:
            return False

        message = f"{parts[0]}.{parts[1]}".encode("utf-8")
        signature = _base64url_decode(parts[2])

        public_key = _rsa_public_key_from_jwk(jwk)

        # RS256 = RSA with SHA-256
        public_key.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as exc:
        logger.debug("Signature verification failed: %s", exc)
        return False


def _find_jwk_by_kid(jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, str]]:
    """Find the JWK matching the given key ID."""
    keys = jwks.get("keys", [])
    for key in keys:
        if key.get("kid") == kid:
            return key
    return None


def _validate_standard_claims(
    payload: Dict[str, Any],
    config: CognitoJwtConfig,
    require_client_id: bool = True,
) -> Tuple[bool, str]:
    """Validate standard JWT claims for Cognito ID tokens.

    Returns (is_valid, error_message).
    """
    now = time.time()

    # Check expiration
    exp = payload.get("exp")
    if exp is not None:
        try:
            if now > float(exp):
                return False, "Token has expired"
        except (TypeError, ValueError):
            return False, "Invalid exp claim"

    # Check not-before (optional, but good to validate)
    nbf = payload.get("nbf")
    if nbf is not None:
        try:
            if now < float(nbf):
                return False, "Token not yet valid"
        except (TypeError, ValueError):
            return False, "Invalid nbf claim"

    # Check issuer
    iss = payload.get("iss", "")
    expected_issuer = config.issuer
    if iss != expected_issuer:
        return False, f"Invalid issuer: {iss}"

    # Check audience (aud) - should match one of the app client IDs for ID tokens
    aud = payload.get("aud")
    if require_client_id and aud is not None:
        if not config.client_ids:
            return False, "No valid client IDs configured"
        if aud not in config.client_ids:
            return False, f"Invalid audience: {aud}"

    # Check token_use - should be "id" for ID tokens
    token_use = payload.get("token_use", "")
    if token_use and token_use not in ("id", "access"):
        return False, f"Invalid token_use: {token_use}"

    return True, ""


def verify_cognito_token(
    token: str,
    config: Optional[CognitoJwtConfig],
) -> Optional[VerifiedClaims]:
    """Verify a Cognito JWT token signature and standard claims.

    This is the secure replacement for _parse_jwt_claims_unverified.

    Args:
        token: The JWT token string (including signature).
        config: Cognito JWT configuration with pool ID, client IDs, and region.

    Returns:
        VerifiedClaims if the token is valid, None otherwise.
    """
    if not config or not config.user_pool_id or not config.region:
        logger.debug("Cognito JWT config not available, cannot verify token")
        return None

    if not token or token.count(".") != 2:
        return None

    # Decode header to get key ID
    header = _decode_jwt_header(token)
    kid = header.get("kid")
    if not kid:
        logger.debug("JWT header missing kid")
        return None

    # Get JWKS and find matching key
    jwks = _get_cached_jwks(config)
    jwk = _find_jwk_by_kid(jwks, kid)
    if not jwk:
        logger.debug("No matching JWK found for kid: %s", kid)
        return None

    # Verify signature
    if not _verify_signature(token, jwk):
        logger.debug("JWT signature verification failed")
        return None

    # Decode payload
    payload = _decode_jwt_payload(token)
    if not payload:
        return None

    # Validate standard claims
    is_valid, error_msg = _validate_standard_claims(payload, config)
    if not is_valid:
        logger.debug("JWT claim validation failed: %s", error_msg)
        return None

    # Extract relevant claims
    sub = payload.get("sub", "")
    if not sub:
        logger.debug("JWT missing sub claim")
        return None

    role = payload.get("custom:role", "")
    email = payload.get("email")

    return VerifiedClaims(
        sub=sub,
        role=role,
        email=email,
        claims=payload,
    )


def parse_jwt_claims_verified(
    token: str,
    config: Optional[CognitoJwtConfig],
) -> Dict[str, Any]:
    """Parse and verify JWT claims, returning a dict compatible with apigw_cognito_claims.

    Returns empty dict if verification fails (fail-secure).
    """
    verified = verify_cognito_token(token, config)
    if not verified:
        return {}

    # Return a dict that mimics the API Gateway authorizer claims format
    # so the rest of the code doesn't need to change
    return {
        "sub": verified.sub,
        "custom:role": verified.role,
        "email": verified.email or "",
        "aud": verified.claims.get("aud", ""),
        "iss": verified.claims.get("iss", ""),
        "token_use": verified.claims.get("token_use", ""),
        "cognito:username": verified.claims.get("cognito:username", ""),
        "cognito:groups": verified.claims.get("cognito:groups", []),
    }


# Testing hook to clear the JWKS cache
def _clear_jwks_cache_for_tests() -> None:
    """Clear the JWKS cache. Only for unit tests."""
    global _jwks_cache, _jwks_cache_expiry
    _jwks_cache = {}
    _jwks_cache_expiry = 0.0
