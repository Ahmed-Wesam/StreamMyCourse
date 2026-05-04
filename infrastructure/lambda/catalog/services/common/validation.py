from __future__ import annotations

import base64
import json
from typing import Any, Dict

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

