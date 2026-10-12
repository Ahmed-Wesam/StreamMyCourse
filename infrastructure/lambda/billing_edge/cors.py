"""CORS helpers for browser-facing billing manage routes (mirrors catalog pick_origin)."""

from __future__ import annotations

from typing import List, Optional


def parse_allowed_origins(raw: str | None) -> List[str]:
    if not raw or not raw.strip():
        return []
    parts = [p.strip() for p in raw.split(",")]
    return [p for p in parts if p]


def pick_origin(allowed_origins: List[str], request_origin: str | None) -> Optional[str]:
    if not allowed_origins:
        return None
    if allowed_origins == ["*"]:
        return request_origin or "*"
    if request_origin and request_origin in allowed_origins:
        return request_origin
    return allowed_origins[0]
