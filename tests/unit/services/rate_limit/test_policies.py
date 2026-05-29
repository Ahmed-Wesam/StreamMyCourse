"""Unit tests for rate-limit route classification and bucket keys."""

from __future__ import annotations

import pytest

from services.rate_limit.models import RateLimitPolicy
from services.rate_limit.policies import (
    build_bucket_key,
    classify_route,
    resolve_actor,
)


def _policy_ids(policies: list[RateLimitPolicy]) -> list[str]:
    return [p.policy_id for p in policies]


class TestResolveActor:
    def test_uses_sub_when_present(self) -> None:
        assert resolve_actor({"sub": "user-abc"}, "203.0.113.1") == "user-abc"

    def test_falls_back_to_ip_when_sub_missing(self) -> None:
        assert resolve_actor({}, "203.0.113.9") == "203.0.113.9"

    def test_falls_back_to_ip_when_sub_blank(self) -> None:
        assert resolve_actor({"sub": "   "}, "10.0.0.1") == "10.0.0.1"


class TestClassifyRouteProgress:
    _parts = ["courses", "c1", "lessons", "l1", "progress"]

    def test_put_progress_returns_lesson_and_global_policies(self) -> None:
        policies = classify_route("PUT", self._parts, {"sub": "s1", "custom:role": "student"})
        assert policies is not None
        assert _policy_ids(policies) == ["progress.lesson", "progress.sub"]

    def test_teacher_bypass_returns_none(self) -> None:
        assert classify_route("PUT", self._parts, {"sub": "t1", "custom:role": "teacher"}) is None

    def test_admin_bypass_returns_none(self) -> None:
        assert classify_route("PUT", self._parts, {"sub": "a1", "custom:role": "admin"}) is None

    def test_role_claim_fallback(self) -> None:
        assert classify_route("PUT", self._parts, {"sub": "t1", "role": "Teacher"}) is None


class TestClassifyRoutePlayback:
    _parts = ["playback", "c1", "l1"]

    def test_get_playback_policies(self) -> None:
        policies = classify_route("GET", self._parts, {"sub": "s1"})
        assert policies is not None
        assert _policy_ids(policies) == ["playback.lesson", "playback.sub"]

    def test_teacher_still_rate_limited_on_playback(self) -> None:
        policies = classify_route("GET", self._parts, {"sub": "t1", "custom:role": "teacher"})
        assert policies is not None
        assert _policy_ids(policies) == ["playback.lesson", "playback.sub"]


class TestClassifyRouteQuiz:
    _start = ["courses", "c1", "modules", "m1", "quiz", "start"]
    _submit = ["courses", "c1", "modules", "m1", "quiz", "submit"]

    @pytest.mark.parametrize("parts", [_start, _submit])
    def test_quiz_post_policies(self, parts: list[str]) -> None:
        policies = classify_route("POST", parts, {"sub": "s1"})
        assert policies is not None
        assert _policy_ids(policies) == ["quiz.module", "quiz.sub"]

    def test_teacher_bypass_on_quiz(self) -> None:
        assert classify_route("POST", self._start, {"sub": "t1", "custom:role": "teacher"}) is None


class TestClassifyRouteEnroll:
    _parts = ["courses", "c1", "enroll"]

    def test_post_enroll_policy(self) -> None:
        policies = classify_route("POST", self._parts, {"sub": "s1"})
        assert policies is not None
        assert _policy_ids(policies) == ["enroll.sub"]

    def test_admin_bypass_on_enroll(self) -> None:
        assert classify_route("POST", self._parts, {"sub": "a1", "custom:role": "admin"}) is None


class TestClassifyRouteCatalog:
    @pytest.mark.parametrize(
        "parts",
        [
            ["courses"],
            ["courses", "c1"],
            ["courses", "c1", "modules"],
            ["courses", "c1", "lessons"],
        ],
    )
    def test_get_catalog_single_policy(self, parts: list[str]) -> None:
        policies = classify_route("GET", parts, {})
        assert policies is not None
        assert _policy_ids(policies) == ["catalog.actor"]

    def test_teacher_catalog_still_limited(self) -> None:
        policies = classify_route("GET", ["courses"], {"sub": "t1", "custom:role": "teacher"})
        assert policies is not None
        assert _policy_ids(policies) == ["catalog.actor"]


class TestClassifyRouteNoPolicy:
    def test_unmatched_route_returns_none(self) -> None:
        assert classify_route("DELETE", ["courses", "c1"], {"sub": "s1"}) is None

    def test_post_create_course_returns_none(self) -> None:
        assert classify_route("POST", ["courses"], {"sub": "s1"}) is None

    def test_get_course_progress_aggregate_returns_none(self) -> None:
        assert classify_route("GET", ["courses", "c1", "progress"], {"sub": "s1"}) is None

    def test_get_courses_mine_not_catalog_scrape_bucket(self) -> None:
        assert classify_route("GET", ["courses", "mine"], {"sub": "t1", "custom:role": "teacher"}) is None


class TestPolicyLimits:
    def test_progress_limits(self) -> None:
        policies = classify_route(
            "PUT",
            ["courses", "c", "lessons", "l", "progress"],
            {"sub": "s"},
        )
        assert policies is not None
        by_id = {p.policy_id: p for p in policies}
        assert by_id["progress.lesson"].max_count == 6
        assert by_id["progress.lesson"].window_seconds == 60
        assert by_id["progress.sub"].max_count == 60

    def test_playback_limits(self) -> None:
        policies = classify_route("GET", ["playback", "c", "l"], {"sub": "s"})
        assert policies is not None
        by_id = {p.policy_id: p for p in policies}
        assert by_id["playback.lesson"].max_count == 20
        assert by_id["playback.sub"].max_count == 120

    def test_quiz_limits(self) -> None:
        policies = classify_route(
            "POST",
            ["courses", "c", "modules", "m", "quiz", "start"],
            {"sub": "s"},
        )
        assert policies is not None
        by_id = {p.policy_id: p for p in policies}
        assert by_id["quiz.module"].max_count == 30
        assert by_id["quiz.sub"].max_count == 60

    def test_enroll_and_catalog_limits(self) -> None:
        enroll = classify_route("POST", ["courses", "c", "enroll"], {"sub": "s"})
        assert enroll is not None
        assert enroll[0].max_count == 30
        catalog = classify_route("GET", ["courses"], {})
        assert catalog is not None
        assert catalog[0].max_count == 300


class TestBuildBucketKey:
    def test_progress_lesson_key(self) -> None:
        policies = classify_route(
            "PUT",
            ["courses", "c1", "lessons", "l1", "progress"],
            {"sub": "sub-1"},
        )
        assert policies is not None
        key = build_bucket_key(policies[0], actor="sub-1", parts=["courses", "c1", "lessons", "l1", "progress"])
        assert key == "rl:progress:lesson:sub-1:l1"

    def test_progress_sub_global_key(self) -> None:
        policies = classify_route(
            "PUT",
            ["courses", "c1", "lessons", "l1", "progress"],
            {"sub": "sub-1"},
        )
        assert policies is not None
        key = build_bucket_key(policies[1], actor="sub-1", parts=["courses", "c1", "lessons", "l1", "progress"])
        assert key == "rl:progress:sub:sub-1"

    def test_playback_lesson_key(self) -> None:
        policies = classify_route("GET", ["playback", "c9", "l9"], {"sub": "u"})
        assert policies is not None
        key = build_bucket_key(policies[0], actor="u", parts=["playback", "c9", "l9"])
        assert key == "rl:playback:lesson:u:l9"

    def test_quiz_module_key(self) -> None:
        policies = classify_route(
            "POST",
            ["courses", "c1", "modules", "m42", "quiz", "submit"],
            {"sub": "stu"},
        )
        assert policies is not None
        key = build_bucket_key(
            policies[0],
            actor="stu",
            parts=["courses", "c1", "modules", "m42", "quiz", "submit"],
        )
        assert key == "rl:quiz:module:stu:m42"

    def test_catalog_key_uses_actor(self) -> None:
        policies = classify_route("GET", ["courses"], {})
        assert policies is not None
        key = build_bucket_key(policies[0], actor="198.51.100.2", parts=["courses"])
        assert key == "rl:catalog:actor:198.51.100.2"
