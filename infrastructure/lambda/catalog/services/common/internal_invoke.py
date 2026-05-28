"""Structured success/error payloads for direct Lambda invoke handlers."""

from __future__ import annotations

from typing import Any, Callable, Dict

from services.common.errors import HttpError


def internal_invoke_success(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, **data}


def internal_invoke_error(
    *,
    status_code: int,
    code: str,
    message: str,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "statusCode": status_code,
        "code": code,
        "message": message,
    }


def run_internal_handler(handler: Callable[..., Dict[str, Any]], *args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Map domain HttpError to structured invoke errors (no Lambda FunctionError)."""
    try:
        result = handler(*args, **kwargs)
    except HttpError as exc:
        return internal_invoke_error(
            status_code=exc.status_code,
            code=str(exc.code or "error"),
            message=exc.message,
        )
    except ValueError as exc:
        return internal_invoke_error(
            status_code=400,
            code="invalid_request",
            message=str(exc),
        )

    if not isinstance(result, dict):
        raise TypeError("internal handler must return a dict")

    error_code = str(result.get("errorCode") or "").strip()
    if error_code:
        status = 409 if error_code == "upload_conflict" else 400
        return internal_invoke_error(
            status_code=status,
            code=error_code,
            message=str(result.get("message") or error_code),
        )

    return internal_invoke_success(result)
