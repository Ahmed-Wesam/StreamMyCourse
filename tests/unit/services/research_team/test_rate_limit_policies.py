"""RS-14 rate-limit policy classification for research team routes."""

from __future__ import annotations

from services.rate_limit.policies import classify_route


def test_classify_research_team_requirements_public_get() -> None:
    policies = classify_route("GET", ["research-team", "requirements"], {})
    assert policies is not None
    assert [p.policy_id for p in policies] == [
        "research_team.requirements.ip",
        "research_team.requirements.global",
    ]
    assert policies[0].max_count == 20
    assert policies[0].window_seconds == 600
    assert policies[1].max_count == 200
    assert policies[1].window_seconds == 3600


def test_classify_research_team_apply_post() -> None:
    policies = classify_route(
        "POST",
        ["me", "research-team", "applications"],
        {"sub": "student-1"},
    )
    assert policies is not None
    assert [p.policy_id for p in policies] == ["research_team.apply"]
    assert policies[0].max_count == 5
    assert policies[0].window_seconds == 600


def test_classify_research_team_does_not_confuse_adjacent_paths() -> None:
    assert classify_route("GET", ["me", "research-team"], {"sub": "s"}) is None
    assert classify_route("GET", ["research-team", "applications"], {"sub": "a"}) is None
    assert (
        classify_route(
            "POST",
            ["research-team", "applications", "id1", "allow-reapply"],
            {"sub": "a"},
        )
        is None
    )
