from __future__ import annotations

import base64
import json
from typing import Any, Dict, Union

from services.common.errors import BadRequest


def parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw_body = event.get("body")
    is_b64 = bool(event.get("isBase64Encoded"))

    if raw_body is None:
        return {}
    if isinstance(raw_body, dict):
        return raw_body
    if not isinstance(raw_body, str):
        raise BadRequest("Request body must be JSON")

    text = raw_body or "{}"
    if is_b64:
        try:
            text = base64.b64decode(text).decode("utf-8")
        except Exception as e:
            raise BadRequest("Invalid base64-encoded request body") from e

    try:
        parsed = json.loads(text)
    except Exception as e:
        raise BadRequest("Request body must be valid JSON") from e

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise BadRequest("Request body must be a JSON object")
    return parsed


def require_str(body: Dict[str, Any], key: str) -> str:
    val = body.get(key)
    if not isinstance(val, str) or not val.strip():
        raise BadRequest(f"'{key}' is required")
    return val.strip()


def optional_str(body: Dict[str, Any], key: str, default: str = "") -> str:
    val = body.get(key)
    return val.strip() if isinstance(val, str) else default


def require_int(body: Dict[str, Any], key: str) -> int:
    """Extract and validate required integer field from body.

    Args:
        body: Parsed JSON body
        key: Field name

    Returns:
        Integer value

    Raises:
        BadRequest: If field is missing or not a valid integer
    """
    val = body.get(key)
    if val is None:
        raise BadRequest(f"'{key}' is required")
    if isinstance(val, bool):
        raise BadRequest(f"'{key}' must be a number, not a boolean")
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        try:
            return int(val)
        except ValueError:
            raise BadRequest(f"'{key}' must be a valid integer")
    raise BadRequest(f"'{key}' must be a number")


def require_json_array_or_object(body: Dict[str, Any], key: str) -> Union[list[Any], dict[str, Any]]:
    """Require a JSON field that is a non-null array or object (e.g. ``optionsJson``)."""
    val = body.get(key)
    if val is None:
        raise BadRequest(f"'{key}' is required")
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return val
    raise BadRequest(f"'{key}' must be a JSON array or object")


def optional_bool(body: Dict[str, Any], key: str, *, default: bool = False) -> bool:
    """Optional boolean field (missing key → ``default``); rejects non-booleans."""
    if key not in body:
        return default
    val = body[key]
    if isinstance(val, bool):
        return val
    raise BadRequest(f"'{key}' must be a boolean")


def require_string_mapping(body: Dict[str, Any], key: str) -> Dict[str, str]:
    """Require a JSON object whose keys and values are non-empty strings."""
    val = body.get(key)
    if val is None:
        raise BadRequest(f"'{key}' is required")
    if not isinstance(val, dict):
        raise BadRequest(f"'{key}' must be a JSON object")
    out: Dict[str, str] = {}
    for raw_k, raw_v in val.items():
        if not isinstance(raw_k, str) or not raw_k.strip():
            raise BadRequest(f"'{key}' keys must be non-empty strings")
        if not isinstance(raw_v, str) or not raw_v.strip():
            raise BadRequest(f"'{key}' values must be non-empty strings")
        out[raw_k.strip()] = raw_v.strip()
    return out

