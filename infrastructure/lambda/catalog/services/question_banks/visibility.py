"""Pure helpers for module quiz visibility (QB-D)."""

from __future__ import annotations


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
