from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# Defense-in-depth for JSON API responses (limited effect on fetch/XHR; avoids silent removal).
_CSP_API = "default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


@dataclass(frozen=True)
class CorsConfig:
    allowed_origins: List[str]


def pick_origin(allowed_origins: List[str], request_origin: str | None) -> Optional[str]:
    """Return CORS ``Access-Control-Allow-Origin`` value, or ``None`` to omit CORS headers.

    Empty ``allowed_origins`` means the caller should reject the request (misconfiguration).
    Explicit ``["*"]`` (from env ``ALLOWED_ORIGINS=*``) echoes the request origin or ``*``.
    """
    if not allowed_origins:
        return None
    if allowed_origins == ["*"]:
        return request_origin or "*"
    if request_origin and request_origin in allowed_origins:
        return request_origin
    return allowed_origins[0]


def _security_headers(origin: Optional[str]) -> Dict[str, str]:
    h: Dict[str, str] = {
        "content-type": "application/json",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": _CSP_API,
        # Never cache JSON API bodies (esp. GET /courses); stale catalog lists after DELETE
        # were observed when only error responses set no-store.
        "Cache-Control": "no-store",
    }
    if origin is not None:
        h["Access-Control-Allow-Origin"] = origin
        h["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        h["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        if origin.startswith("https://"):
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return h


def json_response(status_code: int, body: Any, origin: Optional[str]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": _security_headers(origin),
        "body": json.dumps(body),
    }


def options_response(origin: Optional[str]) -> Dict[str, Any]:
    h: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": _CSP_API,
    }
    if origin is not None:
        h["Access-Control-Allow-Origin"] = origin
        h["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        h["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
        if origin.startswith("https://"):
            h["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return {
        "statusCode": 204,
        "headers": h,
        "body": "",
    }


_API_ROOTS = frozenset({"courses", "playback", "upload-url", "users"})


def _strip_api_stage_prefix(stage: object, path: str) -> str:
    """Remove ``/{stage}/`` when API Gateway puts the stage first in ``path``/``rawPath``."""
    if not isinstance(stage, str) or not stage:
        return path
    prefix = f"/{stage}/"
    if path.startswith(prefix):
        return "/" + path[len(prefix) :]
    if path in (f"/{stage}", f"/{stage}/"):
        return "/"
    return path


def _strip_leading_stage_segment(path: str) -> str:
    """If ``stage`` was missing, drop a first segment when it looks like a stage (``/staging/courses/...``)."""
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] not in _API_ROOTS and parts[1] in _API_ROOTS:
        return "/" + "/".join(parts[1:])
    return path


def _normalize_gateway_path(stage: object, path: str) -> str:
    p = _strip_api_stage_prefix(stage, path)
    return _strip_leading_stage_segment(p)


def apigw_routing_path(event: Dict[str, Any]) -> str:
    """Path for URL routing (literal segments, no ``{…}`` placeholders).

    ``requestContext.resourcePath`` is often a **template** (e.g. ``/courses/{courseId}``); we only
    use it when it contains no ``{``. For ``path`` / ``rawPath``, **prefer ``path``** when it is
    literal: some integrations set ``rawPath`` to the template while ``path`` carries the real URL.
    """
    rc = event.get("requestContext") or {}
    stage = rc.get("stage")
    resource_path = rc.get("resourcePath")
    if (
        isinstance(resource_path, str)
        and resource_path.startswith("/")
        and "{" not in resource_path
    ):
        return _normalize_gateway_path(stage, resource_path)

    path = event.get("path")
    raw = event.get("rawPath")
    for candidate in (path, raw):
        if isinstance(candidate, str) and candidate.startswith("/") and "{" not in candidate:
            return _normalize_gateway_path(stage, candidate)
    for candidate in (path, raw):
        if isinstance(candidate, str) and candidate.startswith("/"):
            return _normalize_gateway_path(stage, candidate)
    return "/"


_SKIP_AUTHORIZER_META = frozenset({"claims", "principalId", "integrationLatency", "scopes"})


def apigw_cognito_claims(
    event: Dict[str, Any],
    *,
    jwt_config: "CognitoJwtConfig | None" = None,
) -> Dict[str, Any]:
    """JWT claims for request authorization.

    Prefer API Gateway authorizer claims when present (already-authenticated).

    For **public** routes that intentionally do not attach an authorizer (for example,
    `GET /courses/{id}/modules`), API Gateway will not populate `requestContext.authorizer`
    even if the caller supplies an `Authorization: Bearer ...` header. In that case, we
    optionally verify the JWT inside the Lambda (fail-secure) so draft-only behavior can
    still be scoped to the caller when a valid token is provided.
    """
    auth = event.get("requestContext", {}).get("authorizer") or {}
    claims: Dict[str, Any] | None = None

    if isinstance(auth, dict):
        nested = auth.get("claims")
        if isinstance(nested, dict) and nested:
            claims = nested
        elif isinstance(nested, str) and nested.strip():
            try:
                parsed = json.loads(nested)
                if isinstance(parsed, dict) and parsed:
                    claims = parsed
            except json.JSONDecodeError:
                pass
        if claims is None and isinstance(auth.get("sub"), str):
            claims = {k: v for k, v in auth.items() if k not in _SKIP_AUTHORIZER_META}

    if claims is not None:
        return claims

    # Optional fallback: verify Authorization bearer token when no authorizer was attached.
    if jwt_config is not None:
        headers = event.get("headers") or {}
        raw = headers.get("authorization") or headers.get("Authorization") or ""
        s = str(raw or "").strip()
        if s.lower().startswith("bearer "):
            token = s.split(" ", 1)[1].strip()
            if token:
                # Local import keeps cold-start path lean for stacks that never use this fallback.
                from services.common.jwt_verify import parse_jwt_claims_verified

                verified_claims = parse_jwt_claims_verified(token, jwt_config)
                if verified_claims:
                    return verified_claims

    return {}

