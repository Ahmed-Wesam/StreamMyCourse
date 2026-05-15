"""Unit tests for module quiz visibility merge (QB-D slice 2)."""

from __future__ import annotations

import pytest

from services.question_banks.visibility import apply_module_quiz_visibility

_SAMPLE_REPO_MAP = {
    "module-a": {"servedCountN": 2},
    "module-b": {"servedCountN": 5},
}


@pytest.mark.parametrize(
    ("course_status", "has_lesson_access", "repo_map", "expected"),
    [
        ("DRAFT", True, _SAMPLE_REPO_MAP, {}),
        ("PUBLISHED", False, _SAMPLE_REPO_MAP, {}),
        (
            "PUBLISHED",
            True,
            _SAMPLE_REPO_MAP,
            {
                "module-a": {"available": True, "servedCountN": 2},
                "module-b": {"available": True, "servedCountN": 5},
            },
        ),
        ("PUBLISHED", True, {}, {}),
    ],
)
def test_apply_module_quiz_visibility(
    course_status: str,
    has_lesson_access: bool,
    repo_map: dict[str, dict[str, int]],
    expected: dict[str, dict[str, object]],
) -> None:
    result = apply_module_quiz_visibility(
        repo_map,
        course_status=course_status,
        has_lesson_access=has_lesson_access,
    )
    assert result == expected
