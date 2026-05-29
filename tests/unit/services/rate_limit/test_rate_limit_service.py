"""Unit tests for ``RateLimitService`` (repository port seam)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pytest

from services.common.errors import RateLimitStoreError, TooManyRequests
from services.rate_limit.models import RateLimitContext, RateLimitResult
from services.rate_limit.service import RateLimitService


@dataclass
class FakeRateLimitRepo:
    outcomes: List[RateLimitResult] = field(default_factory=list)
    calls: list[tuple[str, int, int]] = field(default_factory=list)
    raise_on_consume: Exception | None = None

    def consume(self, bucket_key: str, window_seconds: int, max_count: int) -> RateLimitResult:
        self.calls.append((bucket_key, window_seconds, max_count))
        if self.raise_on_consume is not None:
            raise self.raise_on_consume
        if not self.outcomes:
            return RateLimitResult(allowed=True, retry_after_seconds=0)
        return self.outcomes.pop(0)


def _progress_ctx() -> RateLimitContext:
    return RateLimitContext(
        method="PUT",
        parts=["courses", "c1", "lessons", "l1", "progress"],
        claims={"sub": "student-1", "custom:role": "student"},
        source_ip="10.0.0.1",
    )


class TestRateLimitServiceAllow:
    def test_allows_when_all_buckets_under_limit(self) -> None:
        repo = FakeRateLimitRepo(
            outcomes=[
                RateLimitResult(allowed=True),
                RateLimitResult(allowed=True),
            ]
        )
        svc = RateLimitService(repo)
        svc.check(_progress_ctx())
        assert len(repo.calls) == 2

    def test_no_op_when_route_has_no_policy(self) -> None:
        repo = FakeRateLimitRepo()
        svc = RateLimitService(repo)
        svc.check(
            RateLimitContext(
                method="GET",
                parts=["users", "me"],
                claims={"sub": "s1"},
                source_ip="10.0.0.1",
            )
        )
        assert repo.calls == []


class TestRateLimitServiceDeny:
    def test_raises_too_many_requests_when_bucket_at_limit(self) -> None:
        repo = FakeRateLimitRepo(
            outcomes=[
                RateLimitResult(allowed=True),
                RateLimitResult(allowed=False, retry_after_seconds=42),
            ]
        )
        svc = RateLimitService(repo)
        with pytest.raises(TooManyRequests) as exc_info:
            svc.check(_progress_ctx())
        assert exc_info.value.code == "rate_limited"
        assert exc_info.value.retry_after_seconds == 42
        assert len(repo.calls) == 2

    def test_stops_after_first_denied_bucket(self) -> None:
        repo = FakeRateLimitRepo(
            outcomes=[RateLimitResult(allowed=False, retry_after_seconds=5)]
        )
        svc = RateLimitService(repo)
        with pytest.raises(TooManyRequests):
            svc.check(_progress_ctx())
        assert len(repo.calls) == 1


class TestRateLimitServiceFailClosed:
    def test_repo_exception_propagates_as_store_error(self) -> None:
        repo = FakeRateLimitRepo(raise_on_consume=RuntimeError("db down"))
        svc = RateLimitService(repo)
        with pytest.raises(RateLimitStoreError) as exc_info:
            svc.check(_progress_ctx())
        assert exc_info.value.status_code == 503
        assert len(repo.calls) == 1

    def test_does_not_allow_when_repo_fails(self) -> None:
        repo = FakeRateLimitRepo(raise_on_consume=OSError("timeout"))
        svc = RateLimitService(repo)
        with pytest.raises(RateLimitStoreError):
            svc.check(_progress_ctx())


class TestRateLimitServiceMaxOverrides:
    def test_override_replaces_policy_max_count(self) -> None:
        repo = FakeRateLimitRepo(
            outcomes=[
                RateLimitResult(allowed=True),
                RateLimitResult(allowed=True),
            ]
        )
        svc = RateLimitService(repo, max_overrides={"progress.lesson": 99})
        svc.check(_progress_ctx())
        assert repo.calls[0][2] == 99
        assert repo.calls[1][2] == 60


class TestRateLimitServiceBypass:
    def test_teacher_skips_checks(self) -> None:
        repo = FakeRateLimitRepo()
        svc = RateLimitService(repo)
        svc.check(
            RateLimitContext(
                method="PUT",
                parts=["courses", "c1", "lessons", "l1", "progress"],
                claims={"sub": "t1", "custom:role": "teacher"},
                source_ip="10.0.0.1",
            )
        )
        assert repo.calls == []
