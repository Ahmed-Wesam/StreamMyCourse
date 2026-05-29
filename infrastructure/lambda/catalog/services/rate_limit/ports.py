from __future__ import annotations

from typing import Protocol

from services.rate_limit.models import RateLimitResult


class RateLimitRepositoryPort(Protocol):
    """Persistence adapter for fixed-window rate counters (RDS in a later slice)."""

    def consume(
        self,
        bucket_key: str,
        window_seconds: int,
        max_count: int,
    ) -> RateLimitResult:
        """Record one request against ``bucket_key`` and return whether it is allowed."""
        ...
