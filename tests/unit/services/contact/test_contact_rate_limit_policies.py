"""Rate-limit classification for POST /contact."""

from __future__ import annotations

from services.rate_limit.policies import build_bucket_key, classify_route


def _policy_ids(method: str, parts: list[str]) -> list[str]:
    policies = classify_route(method, parts, {})
    assert policies is not None
    return [p.policy_id for p in policies]


class TestPostContactRateLimit:
    def test_post_contact_policies(self) -> None:
        assert _policy_ids("POST", ["contact"]) == ["contact.ip", "contact.global"]

    def test_contact_ip_limits(self) -> None:
        policies = classify_route("POST", ["contact"], {})
        assert policies is not None
        by_id = {p.policy_id: p for p in policies}
        assert by_id["contact.ip"].max_count == 5
        assert by_id["contact.ip"].window_seconds == 600
        assert by_id["contact.global"].max_count == 30
        assert by_id["contact.global"].window_seconds == 3600

    def test_contact_ip_bucket_uses_actor(self) -> None:
        policies = classify_route("POST", ["contact"], {})
        assert policies is not None
        key = build_bucket_key(policies[0], actor="203.0.113.5", parts=["contact"])
        assert key == "rl:contact:ip:203.0.113.5"

    def test_contact_global_bucket_constant(self) -> None:
        policies = classify_route("POST", ["contact"], {})
        assert policies is not None
        key = build_bucket_key(policies[1], actor="ignored", parts=["contact"])
        assert key == "rl:contact:global"
