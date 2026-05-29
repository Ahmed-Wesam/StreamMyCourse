from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class RateLimitPolicy:
    """A single sliding-window counter policy applied to one bucket key."""

    policy_id: str
    window_seconds: int
    max_count: int
    bucket_key_template: str


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: int = 0


@dataclass(frozen=True)
class RateLimitContext:
    """Inputs for a single HTTP request (no API Gateway event types)."""

    method: str
    parts: Tuple[str, ...]
    claims: Mapping[str, Any]
    source_ip: str
