"""Preview DSQL row counts for lesson progress and notes (DSQL-4 S6)."""

from __future__ import annotations

from typing import Any

from helpers.dsql_audit import execute_scalar


def count_progress_for_lesson(conn: Any, *, course_id: str, lesson_id: str) -> int:
    return int(
        execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.lesson_progress WHERE course_id = %s AND lesson_id = %s",
            (course_id, lesson_id),
        )
        or 0
    )


def count_notes_for_lesson(conn: Any, *, course_id: str, lesson_id: str) -> int:
    return int(
        execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.lesson_notes WHERE course_id = %s AND lesson_id = %s",
            (course_id, lesson_id),
        )
        or 0
    )


def count_progress_for_course(conn: Any, course_id: str) -> int:
    return int(
        execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.lesson_progress WHERE course_id = %s",
            (course_id,),
        )
        or 0
    )


def count_notes_for_course(conn: Any, course_id: str) -> int:
    return int(
        execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.lesson_notes WHERE course_id = %s",
            (course_id,),
        )
        or 0
    )
