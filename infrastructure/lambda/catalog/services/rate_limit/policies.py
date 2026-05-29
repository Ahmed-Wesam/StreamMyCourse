from __future__ import annotations

from typing import Any, Mapping, Sequence

from services.rate_limit.models import RateLimitPolicy

_WINDOW = 60

_PROGRESS_LESSON = RateLimitPolicy(
    policy_id="progress.lesson",
    window_seconds=_WINDOW,
    max_count=6,
    bucket_key_template="rl:progress:lesson:{actor}:{lesson_id}",
)
_PROGRESS_SUB = RateLimitPolicy(
    policy_id="progress.sub",
    window_seconds=_WINDOW,
    max_count=60,
    bucket_key_template="rl:progress:sub:{actor}",
)

_PLAYBACK_LESSON = RateLimitPolicy(
    policy_id="playback.lesson",
    window_seconds=_WINDOW,
    max_count=20,
    bucket_key_template="rl:playback:lesson:{actor}:{lesson_id}",
)
_PLAYBACK_SUB = RateLimitPolicy(
    policy_id="playback.sub",
    window_seconds=_WINDOW,
    max_count=120,
    bucket_key_template="rl:playback:sub:{actor}",
)

_QUIZ_MODULE = RateLimitPolicy(
    policy_id="quiz.module",
    window_seconds=_WINDOW,
    max_count=30,
    bucket_key_template="rl:quiz:module:{actor}:{module_id}",
)
_QUIZ_SUB = RateLimitPolicy(
    policy_id="quiz.sub",
    window_seconds=_WINDOW,
    max_count=60,
    bucket_key_template="rl:quiz:sub:{actor}",
)

_ENROLL_SUB = RateLimitPolicy(
    policy_id="enroll.sub",
    window_seconds=_WINDOW,
    max_count=30,
    bucket_key_template="rl:enroll:sub:{actor}",
)

_CATALOG_ACTOR = RateLimitPolicy(
    policy_id="catalog.actor",
    window_seconds=_WINDOW,
    max_count=300,
    bucket_key_template="rl:catalog:actor:{actor}",
)


def resolve_actor(claims: Mapping[str, Any], source_ip: str) -> str:
    sub = str(claims.get("sub", "") or "").strip()
    if sub:
        return sub
    return (source_ip or "").strip() or "unknown"


def _role_from_claims(claims: Mapping[str, Any]) -> str:
    return str(claims.get("custom:role") or claims.get("role") or "student").strip().lower()


def _skips_student_burst(claims: Mapping[str, Any]) -> bool:
    return _role_from_claims(claims) in ("teacher", "admin")


def _is_put_lesson_progress(method: str, parts: Sequence[str]) -> bool:
    return (
        method == "PUT"
        and len(parts) == 5
        and parts[0] == "courses"
        and parts[2] == "lessons"
        and parts[4] == "progress"
    )


def _is_get_playback(method: str, parts: Sequence[str]) -> bool:
    return method == "GET" and len(parts) == 3 and parts[0] == "playback"


def _is_post_quiz_start_or_submit(method: str, parts: Sequence[str]) -> bool:
    return (
        method == "POST"
        and len(parts) == 6
        and parts[0] == "courses"
        and parts[2] == "modules"
        and parts[4] == "quiz"
        and parts[5] in ("start", "submit")
    )


def _is_post_enroll(method: str, parts: Sequence[str]) -> bool:
    return (
        method == "POST"
        and len(parts) == 3
        and parts[0] == "courses"
        and parts[2] == "enroll"
    )


def _is_get_catalog(method: str, parts: Sequence[str]) -> bool:
    if method != "GET" or not parts or parts[0] != "courses":
        return False
    if parts == ["courses"]:
        return True
    if len(parts) == 2:
        # Instructor dashboard uses GET /courses/mine — not public catalog scraping.
        return parts[1] != "mine"
    if len(parts) == 3 and parts[2] in ("modules", "lessons"):
        return True
    return False


def classify_route(
    method: str,
    parts: Sequence[str],
    claims: Mapping[str, Any],
) -> list[RateLimitPolicy] | None:
    """Return policies to enforce for this route, or ``None`` when unrated / bypassed."""
    normalized_parts = list(parts)

    if _is_put_lesson_progress(method, normalized_parts):
        if _skips_student_burst(claims):
            return None
        return [_PROGRESS_LESSON, _PROGRESS_SUB]

    if _is_get_playback(method, normalized_parts):
        return [_PLAYBACK_LESSON, _PLAYBACK_SUB]

    if _is_post_quiz_start_or_submit(method, normalized_parts):
        if _skips_student_burst(claims):
            return None
        return [_QUIZ_MODULE, _QUIZ_SUB]

    if _is_post_enroll(method, normalized_parts):
        if _skips_student_burst(claims):
            return None
        return [_ENROLL_SUB]

    if _is_get_catalog(method, normalized_parts):
        return [_CATALOG_ACTOR]

    return None


def build_bucket_key(
    policy: RateLimitPolicy,
    *,
    actor: str,
    parts: Sequence[str],
) -> str:
    """Materialize ``policy.bucket_key_template`` from path parts and the resolved actor."""
    lesson_id = ""
    module_id = ""
    if len(parts) >= 4 and parts[0] == "courses" and parts[2] == "lessons":
        lesson_id = parts[3]
    if parts and parts[0] == "playback" and len(parts) >= 3:
        lesson_id = parts[2]
    if len(parts) >= 4 and parts[0] == "courses" and parts[2] == "modules":
        module_id = parts[3]

    return policy.bucket_key_template.format(
        actor=actor,
        lesson_id=lesson_id,
        module_id=module_id,
    )
