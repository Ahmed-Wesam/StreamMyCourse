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


def bind_request_context(
    *,
    lambda_request_id: Optional[str] = None,
    api_request_id: Optional[str] = None,
    http_method: Optional[str] = None,
    route_or_action: Optional[str] = None,
) -> None:
    """Bind request-scoped context variables.

    Call this at the start of a Lambda invocation to set correlation IDs
    and request metadata. All parameters are optional and default to None.

    Args:
        lambda_request_id: The Lambda context aws_request_id
        api_request_id: The API Gateway requestId
        http_method: HTTP method (GET, POST, etc.)
        route_or_action: Route or action name (e.g., "get_course")
    """
    _lambda_request_id.set(lambda_request_id)
    _api_request_id.set(api_request_id)
    _http_method.set(http_method)
    _route_or_action.set(route_or_action)


def clear_request_context() -> None:
    """Clear all request-scoped context variables.

    Call this in a finally block to ensure context is cleaned up after
    each request, preventing context leakage between invocations.
    """
    _lambda_request_id.set(None)
    _api_request_id.set(None)
    _http_method.set(None)
    _route_or_action.set(None)


def get_request_context() -> Dict[str, Optional[str]]:
    """Get the current request context as a dictionary.

    Returns:
        Dict with lambda_request_id, api_request_id, http_method, route_or_action
    """
    return {
        "lambda_request_id": _lambda_request_id.get(),
        "api_request_id": _api_request_id.get(),
        "http_method": _http_method.get(),
        "route_or_action": _route_or_action.get(),
    }


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
        http_method=http_method,
        route_or_action=route_or_action,
    )


def update_action(action: str) -> None:
    """Update just the action field in the context.

    Useful for setting the action after routing is determined.

    Args:
        action: The action name (e.g., "get_course", "create_course")
    """
    _route_or_action.set(action)
