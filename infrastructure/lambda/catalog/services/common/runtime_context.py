"""Runtime context management using contextvars.

Provides request-scoped context for correlation IDs and request metadata.
Each Lambda invocation gets its own isolated context.
"""

from __future__ import annotations

import contextvars
from typing import Any, Dict, Optional

# Context variables for request correlation
_lambda_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "lambda_request_id", default=None
)
_api_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "api_request_id", default=None
)
_http_method: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "http_method", default=None
)
_route_or_action: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "route_or_action", default=None
)
# API Gateway + routing (observability; no secrets)
_api_stage: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("api_stage", default=None)
_api_domain: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("api_domain", default=None)
_route_key: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("route_key", default=None)
_client_ip: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("client_ip", default=None)
_user_agent_snippet: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_agent_snippet", default=None
)
_request_path: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_path", default=None)
_upload_kind: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("upload_kind", default=None)

_USER_AGENT_MAX = 200


def bind_request_context(
    *,
    lambda_request_id: Optional[str] = None,
    api_request_id: Optional[str] = None,
    http_method: Optional[str] = None,
    route_or_action: Optional[str] = None,
    api_stage: Optional[str] = None,
    api_domain: Optional[str] = None,
    route_key: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent_snippet: Optional[str] = None,
    request_path: Optional[str] = None,
    upload_kind: Optional[str] = None,
) -> None:
    """Bind request-scoped context variables.

    Call this at the start of a Lambda invocation to set correlation IDs
    and request metadata. All parameters are optional and default to None.

    Args:
        lambda_request_id: The Lambda context aws_request_id
        api_request_id: The API Gateway requestId
        http_method: HTTP method (GET, POST, etc.)
        route_or_action: Route or action name (e.g., "get_course")
        api_stage: API Gateway stage name (when present)
        api_domain: API Gateway ``domainName`` (host)
        route_key: HTTP API ``routeKey`` or synthesized REST route
        client_ip: Client source IP from API Gateway (when present)
        user_agent_snippet: Truncated User-Agent (when present)
        request_path: Normalized application path used for routing (no stage prefix)
        upload_kind: For ``POST /upload-url`` branches: lesson video vs thumbnail kinds
    """
    _lambda_request_id.set(lambda_request_id)
    _api_request_id.set(api_request_id)
    _http_method.set(http_method)
    _route_or_action.set(route_or_action)
    _api_stage.set(api_stage)
    _api_domain.set(api_domain)
    _route_key.set(route_key)
    _client_ip.set(client_ip)
    _user_agent_snippet.set(user_agent_snippet)
    _request_path.set(request_path)
    _upload_kind.set(upload_kind)


def clear_request_context() -> None:
    """Clear all request-scoped context variables.

    Call this in a finally block to ensure context is cleaned up after
    each request, preventing context leakage between invocations.
    """
    _lambda_request_id.set(None)
    _api_request_id.set(None)
    _http_method.set(None)
    _route_or_action.set(None)
    _api_stage.set(None)
    _api_domain.set(None)
    _route_key.set(None)
    _client_ip.set(None)
    _user_agent_snippet.set(None)
    _request_path.set(None)
    _upload_kind.set(None)


def get_request_context() -> Dict[str, Optional[str]]:
    """Get the current request context as a dictionary."""
    return {
        "lambda_request_id": _lambda_request_id.get(),
        "api_request_id": _api_request_id.get(),
        "http_method": _http_method.get(),
        "route_or_action": _route_or_action.get(),
        "api_stage": _api_stage.get(),
        "api_domain": _api_domain.get(),
        "route_key": _route_key.get(),
        "client_ip": _client_ip.get(),
        "user_agent_snippet": _user_agent_snippet.get(),
        "request_path": _request_path.get(),
        "upload_kind": _upload_kind.get(),
    }


def set_request_path(path: str) -> None:
    """Set normalized routing path (typically after ``apigw_routing_path``)."""
    p = (path or "").strip()
    _request_path.set(p or None)


def set_upload_kind(kind: Optional[str]) -> None:
    """Set upload classification for ``POST /upload-url`` (cleared each request)."""
    if not kind or not str(kind).strip():
        _upload_kind.set(None)
        return
    _upload_kind.set(str(kind).strip())


def extract_apigw_public_fields(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract non-sensitive API Gateway fields for structured logs.

    Supports HTTP API (v2) and REST API (v1) proxy integration shapes.
    """
    out: Dict[str, str] = {}
    if not isinstance(event, dict):
        return out
    rc = event.get("requestContext")
    if not isinstance(rc, dict):
        return out

    stage = rc.get("stage")
    if isinstance(stage, str) and stage.strip():
        out["api_stage"] = stage.strip()

    domain = rc.get("domainName")
    if isinstance(domain, str) and domain.strip():
        out["api_domain"] = domain.strip()

    rk = rc.get("routeKey")
    if isinstance(rk, str) and rk.strip():
        out["route_key"] = rk.strip()

    http = rc.get("http")
    if isinstance(http, dict):
        ip = http.get("sourceIp")
        if isinstance(ip, str) and ip.strip():
            out["client_ip"] = ip.strip()
        ua = http.get("userAgent")
        if isinstance(ua, str) and ua.strip():
            out["user_agent_snippet"] = ua.strip()[:_USER_AGENT_MAX]
        if "route_key" not in out:
            m = http.get("method")
            p = http.get("path")
            if isinstance(m, str) and m.strip():
                path_part = p.strip() if isinstance(p, str) else ""
                out["route_key"] = f"{m.strip()} {path_part}".strip()
    else:
        ident = rc.get("identity")
        if isinstance(ident, dict):
            ip = ident.get("sourceIp")
            if isinstance(ip, str) and ip.strip():
                out["client_ip"] = ip.strip()
        http_method = event.get("httpMethod")
        rp = rc.get("resourcePath")
        if isinstance(http_method, str) and http_method.strip() and isinstance(rp, str):
            out["route_key"] = f"{http_method.strip()} {rp}".strip()

    return out


def extract_api_request_id(event: Dict[str, Any]) -> Optional[str]:
    """Extract API Gateway requestId from event.

    Handles both REST API (requestContext.requestId) and HTTP API
    (requestContext.http.requestId) event formats.

    Args:
        event: API Gateway event dictionary

    Returns:
        The requestId string or None if not found
    """
    if not isinstance(event, dict):
        return None

    request_context = event.get("requestContext")
    if not isinstance(request_context, dict):
        return None

    # Try HTTP API format first (requestContext.http.requestId)
    http_context = request_context.get("http")
    if isinstance(http_context, dict):
        http_request_id = http_context.get("requestId")
        if http_request_id:
            return str(http_request_id)

    # Fall back to REST API format (requestContext.requestId)
    rest_request_id = request_context.get("requestId")
    if rest_request_id:
        return str(rest_request_id)

    return None


def extract_lambda_request_id(lambda_context: Any) -> Optional[str]:
    """Extract aws_request_id from Lambda context.

    Args:
        lambda_context: Lambda context object (typically has aws_request_id attribute)

    Returns:
        The aws_request_id string or None if not available
    """
    if lambda_context is None:
        return None

    # Lambda context is typically an object with aws_request_id attribute
    request_id = getattr(lambda_context, "aws_request_id", None)
    if request_id:
        return str(request_id)

    return None


def bind_from_lambda_event(
    *,
    event: Dict[str, Any],
    lambda_context: Any,
    route_or_action: Optional[str] = None,
) -> None:
    """Convenience helper to bind context from Lambda event and context.

    Extracts request IDs from both sources and binds them.

    Args:
        event: API Gateway event dictionary
        lambda_context: Lambda context object
        route_or_action: Optional action name to set
    """
    lambda_request_id = extract_lambda_request_id(lambda_context)
    api_request_id = extract_api_request_id(event)
    gw = extract_apigw_public_fields(event)

    # Extract HTTP method from event
    http_method = None
    if isinstance(event, dict):
        request_context = event.get("requestContext", {})
        if isinstance(request_context, dict):
            http = request_context.get("http")
            if isinstance(http, dict):
                http_method = http.get("method")
            else:
                # REST API format
                http_method = event.get("httpMethod")

    bind_request_context(
        lambda_request_id=lambda_request_id,
        api_request_id=api_request_id,
        http_method=http_method if isinstance(http_method, str) else None,
        route_or_action=route_or_action,
        api_stage=gw.get("api_stage"),
        api_domain=gw.get("api_domain"),
        route_key=gw.get("route_key"),
        client_ip=gw.get("client_ip"),
        user_agent_snippet=gw.get("user_agent_snippet"),
    )


def update_action(action: str) -> None:
    """Update just the action field in the context.

    Useful for setting the action after routing is determined.

    Args:
        action: The action name (e.g., "get_course", "create_course")
    """
    _route_or_action.set(action)
