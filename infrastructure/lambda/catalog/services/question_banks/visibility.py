"""Pure helpers for module quiz visibility (QB-D)."""

from __future__ import annotations


def module_quiz_score_percent(*, correct_count: int, total_count: int) -> int:
    """Round score to nearest whole percent (half away from zero for ties)."""
    if total_count < 1:
        raise ValueError("total_count must be at least 1")
    return (correct_count * 100 + total_count // 2) // total_count


def apply_module_quiz_visibility(
    repo_map: dict[str, dict[str, int]],
    *,
    course_status: str,
    has_lesson_access: bool,
) -> dict[str, dict[str, object]]:
    """Gate repo visibility by course publish status and lesson access."""
    if course_status != "PUBLISHED" or not has_lesson_access:
        return {}
    return {
        module_id: {"available": True, "servedCountN": entry["servedCountN"]}
        for module_id, entry in repo_map.items()
    }
