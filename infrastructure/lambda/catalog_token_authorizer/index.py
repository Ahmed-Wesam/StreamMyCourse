from __future__ import annotations

import _vendor_bootstrap  # noqa: F401  # prepends _vendor/ to sys.path before deps

import base64
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


_JWKS_CACHE: Dict[str, Dict[str, Any]] = {}
_JWKS_CACHE_EXP: Dict[str, float] = {}
_JWKS_CACHE_TTL_SECONDS = 3600


@dataclass(frozen=True)
class CognitoAuthorizerConfig:
    region: str
    user_pool_id: str
    allowed_client_ids: List[str]

    @property
    def issuer(self) -> str:
        return f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/.well-known/jwks.json"


def _split_csv(raw: str) -> List[str]:
    return [v.strip() for v in (raw or "").split(",") if v.strip()]


def _parse_cognito_pool_arn(arn: str) -> Tuple[str, str]:
    s = (arn or "").strip()
    if not s:
        return ("", "")
    try:
        parts = s.split(":")
        if len(parts) < 6:
            return ("", "")
        region = parts[3]
        last = parts[-1]
        if "/" not in last:
            return ("", "")
        pool_id = last.split("/")[-1]
        return (region, pool_id)
    except Exception:
        return ("", "")


def _load_config_from_env() -> Optional[CognitoAuthorizerConfig]:
    pool_arn = os.environ.get("COGNITO_USER_POOL_ARN", "").strip()
    region, pool_id = _parse_cognito_pool_arn(pool_arn)
    if not region or not pool_id:
        return None

    # Match existing env naming: COGNITO_CLIENT_ID may be comma-separated.
    allowed_client_ids = _split_csv(os.environ.get("COGNITO_CLIENT_ID", ""))
    return CognitoAuthorizerConfig(
        region=region,
        user_pool_id=pool_id,
        allowed_client_ids=allowed_client_ids,
    )


def _base64url_decode(b64url: str) -> bytes:
    pad = 4 - (len(b64url) % 4)
    if pad != 4:
        b64url += "=" * pad
    return base64.urlsafe_b64decode(b64url)


def _decode_jwt_header(token: str) -> Dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        return json.loads(_base64url_decode(parts[0]).decode("utf-8"))
    except Exception:
        return {}


def _decode_jwt_payload(token: str) -> Dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        return json.loads(_base64url_decode(parts[1]).decode("utf-8"))
    except Exception:
        return {}


def _fetch_jwks(jwks_url: str) -> Dict[str, Any]:
    req = urllib.request.Request(jwks_url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_cached_jwks(config: CognitoAuthorizerConfig) -> Dict[str, Any]:
    key = config.user_pool_id
    now = time.time()
    if key in _JWKS_CACHE and now < _JWKS_CACHE_EXP.get(key, 0.0):
        return _JWKS_CACHE[key]

    jwks = _fetch_jwks(config.jwks_url)
    _JWKS_CACHE[key] = jwks
    _JWKS_CACHE_EXP[key] = now + _JWKS_CACHE_TTL_SECONDS
    return jwks


def _find_jwk_by_kid(jwks: Dict[str, Any], kid: str) -> Optional[Dict[str, Any]]:
    for k in jwks.get("keys", []) or []:
        if k.get("kid") == kid:
            return k
    return None


def _verify_signature(token: str, jwk: Dict[str, Any]) -> bool:
    # Separated for unit-test mocking; uses cryptography at runtime.
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        n_b64 = jwk.get("n", "")
        e_b64 = jwk.get("e", "")
        if not n_b64 or not e_b64:
            return False

        parts = token.split(".")
        if len(parts) != 3:
            return False

        message = f"{parts[0]}.{parts[1]}".encode("utf-8")
        signature = _base64url_decode(parts[2])

        n = int.from_bytes(_base64url_decode(n_b64), "big")
        e = int.from_bytes(_base64url_decode(e_b64), "big")
        public_key = rsa.RSAPublicNumbers(e=e, n=n).public_key()

        public_key.verify(signature, message, padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def _validate_claims(payload: Dict[str, Any], config: CognitoAuthorizerConfig) -> bool:
    # Standard validations required by the slice.
    if payload.get("token_use") != "id":
        return False

    iss = payload.get("iss", "")
    if iss != config.issuer:
        return False

    aud = payload.get("aud")
    if config.allowed_client_ids:
        if aud not in config.allowed_client_ids:
            return False

    exp = payload.get("exp")
    if exp is None:
        return False
    try:
        if time.time() > float(exp):
            return False
    except (TypeError, ValueError):
        return False

    return True


def _extract_role(payload: Dict[str, Any]) -> str:
    explicit = (payload.get("custom:role") or "").strip()
    if explicit:
        return explicit
    fallback = os.environ.get("FALLBACK_ROLE", "").strip()
    return fallback or "student"


def _empty_context() -> Dict[str, str]:
    return {"sub": "", "role": "", "email": ""}


def _wildcard_resource(method_arn: str) -> str:
    """Convert a specific method ARN into a wildcard covering all methods on the same API.

    API Gateway caches the authorizer policy per token (AuthorizerResultTtlInSeconds).
    A specific Resource would cause 403 on subsequent calls to different routes.
    """
    # methodArn format: arn:aws:execute-api:{region}:{accountId}:{apiId}/{stage}/{method}/{resource...}
    parts = method_arn.split("/")
    if len(parts) >= 2:
        return parts[0] + "/*"
    return method_arn


def _allow(method_arn: str, principal_id: str, ctx: Dict[str, str]) -> Dict[str, Any]:
    # API Gateway authorizer context values must be strings.
    safe_ctx = {k: str(v or "") for k, v in (ctx or {}).items()}
    return {
        "principalId": principal_id or "anonymous",
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": _wildcard_resource(method_arn)}
            ],
        },
        "context": safe_ctx,
    }


def _extract_bearer_token(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    if s.lower().startswith("bearer "):
        return s[7:].strip()
    return s


def handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    # REQUEST authorizer event shape:
    # - headers: {"Authorization": "Bearer <jwt>", ...}
    # - methodArn: ARN of the invoked method
    method_arn = str((event or {}).get("methodArn") or "*")
    headers = (event or {}).get("headers") or {}
    raw = ""
    if isinstance(headers, dict):
        raw = headers.get("Authorization") or headers.get("authorization") or ""
    token = _extract_bearer_token(str(raw or ""))

    if not token:
        return _allow(method_arn, "anonymous", _empty_context())

    cfg = _load_config_from_env()
    if not cfg:
        return _allow(method_arn, "anonymous", _empty_context())

    try:
        header = _decode_jwt_header(token)
        kid = (header.get("kid") or "").strip()
        if not kid:
            return _allow(method_arn, "anonymous", _empty_context())

        jwks = _get_cached_jwks(cfg)
        jwk = _find_jwk_by_kid(jwks, kid)
        if not jwk:
            return _allow(method_arn, "anonymous", _empty_context())

        if not _verify_signature(token, jwk):
            return _allow(method_arn, "anonymous", _empty_context())

        payload = _decode_jwt_payload(token)
        if not payload:
            return _allow(method_arn, "anonymous", _empty_context())

        if not _validate_claims(payload, cfg):
            return _allow(method_arn, "anonymous", _empty_context())

        sub = str(payload.get("sub") or "")
        email = str(payload.get("email") or "")
        role = _extract_role(payload)

        if not sub:
            return _allow(method_arn, "anonymous", _empty_context())

        return _allow(method_arn, sub, {"sub": sub, "role": str(role or ""), "email": email})
    except Exception:
        return _allow(method_arn, "anonymous", _empty_context())


# CloudFormation template uses `index.lambda_handler` by convention in this repo.
# Keep an alias so handler renames don't break deployments.
lambda_handler = handler

