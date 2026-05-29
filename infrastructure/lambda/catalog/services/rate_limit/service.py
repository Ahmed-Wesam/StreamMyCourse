from __future__ import annotations

from typing import Mapping

from services.common.errors import RateLimitStoreError, TooManyRequests
from services.rate_limit.models import RateLimitContext
from services.rate_limit.policies import build_bucket_key, classify_route, resolve_actor
from services.rate_limit.ports import RateLimitRepositoryPort


class RateLimitService:
    def __init__(
        self,
        repo: RateLimitRepositoryPort,
        *,
        max_overrides: Mapping[str, int] | None = None,
    ) -> None:
        self._repo = repo
        self._max_overrides = dict(max_overrides or {})

    def check(self, ctx: RateLimitContext) -> None:
        """Enforce policies for ``ctx``; raise when limited or when the store is unavailable."""
        policies = classify_route(ctx.method, ctx.parts, ctx.claims)
        if not policies:
            return

        actor = resolve_actor(ctx.claims, ctx.source_ip)
        for policy in policies:
            bucket_key = build_bucket_key(policy, actor=actor, parts=ctx.parts)
            max_count = self._max_overrides.get(policy.policy_id, policy.max_count)
            try:
                result = self._repo.consume(
                    bucket_key,
                    policy.window_seconds,
                    max_count,
                )
            except Exception as exc:
                raise RateLimitStoreError("Rate limit store unavailable") from exc

            if not result.allowed:
                raise TooManyRequests(
                    "Too many requests",
                    retry_after_seconds=result.retry_after_seconds,
                )
