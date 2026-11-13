"""Foreign-key edges in ``0001_schema.sql`` for orphan audits (plans §6.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ForeignKeyEdge:
    """One referential edge: child column(s) must resolve to a parent row."""

    label: str
    child_table: str
    parent_table: str
    child_columns: tuple[str, ...]
    parent_columns: tuple[str, ...]
    require_non_null: tuple[str, ...] = ()

    def parent_pairs_6_1(self) -> tuple[tuple[str, str], ...]:
        return ((self.child_table, self.parent_table),)


def build_orphan_count_sql(edge: ForeignKeyEdge) -> str:
    """``LEFT JOIN ... IS NULL`` orphan count for one FK edge."""
    child = f"app.{edge.child_table} c"
    parent = f"app.{edge.parent_table} p"
    join_cond = " AND ".join(
        f"c.{cc} = p.{pc}" for cc, pc in zip(edge.child_columns, edge.parent_columns)
    )
    parent_anchor = edge.parent_columns[0]
    filters: list[str] = [f"p.{parent_anchor} IS NULL"]
    for col in edge.require_non_null:
        filters.append(f"c.{col} IS NOT NULL")
    where = " AND ".join(filters)
    return (
        f"SELECT COUNT(*) FROM {child} "
        f"LEFT JOIN {parent} ON {join_cond} "
        f"WHERE {where}"
    )


# Maintained alongside infrastructure/database/dsql/0001_schema.sql (§6.1 parents).
DSQL_FOREIGN_KEY_EDGES: tuple[ForeignKeyEdge, ...] = (
    ForeignKeyEdge(
        "course_modules.course_id→courses.id",
        "course_modules",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "lessons.course_id→courses.id",
        "lessons",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "lessons.(course_id,module_id)→course_modules",
        "lessons",
        "course_modules",
        ("course_id", "module_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "lesson_files.(course_id,lesson_id)→lessons",
        "lesson_files",
        "lessons",
        ("course_id", "lesson_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "question_banks.course_id→courses.id",
        "question_banks",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "module_quizzes.course_id→courses.id",
        "module_quizzes",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "module_quizzes.(course_id,module_id)→course_modules",
        "module_quizzes",
        "course_modules",
        ("course_id", "module_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "module_quizzes.(course_id,question_bank_id)→question_banks",
        "module_quizzes",
        "question_banks",
        ("course_id", "question_bank_id"),
        ("course_id", "id"),
        require_non_null=("question_bank_id",),
    ),
    ForeignKeyEdge(
        "questions.course_id→courses.id",
        "questions",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "questions.(course_id,question_bank_id)→question_banks",
        "questions",
        "question_banks",
        ("course_id", "question_bank_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "student_module_quiz_bindings.module_quiz_id→module_quizzes.id",
        "student_module_quiz_bindings",
        "module_quizzes",
        ("module_quiz_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "student_module_quiz_bindings.course_id→courses.id",
        "student_module_quiz_bindings",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "student_module_quiz_bindings.(course_id,module_quiz_id)→module_quizzes",
        "student_module_quiz_bindings",
        "module_quizzes",
        ("course_id", "module_quiz_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "student_module_quiz_binding_questions.binding_id→bindings",
        "student_module_quiz_binding_questions",
        "student_module_quiz_bindings",
        ("binding_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "student_module_quiz_binding_questions.question_id→questions",
        "student_module_quiz_binding_questions",
        "questions",
        ("question_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "module_quiz_attempts.binding_id→bindings",
        "module_quiz_attempts",
        "student_module_quiz_bindings",
        ("binding_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "module_quiz_attempt_submissions.attempt_id→attempts",
        "module_quiz_attempt_submissions",
        "module_quiz_attempts",
        ("attempt_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignments.course_id→courses.id",
        "assignments",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignments.(course_id,module_id)→course_modules",
        "assignments",
        "course_modules",
        ("course_id", "module_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "assignment_criteria.assignment_id→assignments",
        "assignment_criteria",
        "assignments",
        ("assignment_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignment_submissions.assignment_id→assignments",
        "assignment_submissions",
        "assignments",
        ("assignment_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignment_submission_files.submission_id→submissions",
        "assignment_submission_files",
        "assignment_submissions",
        ("submission_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignment_submission_files.assignment_id→assignments",
        "assignment_submission_files",
        "assignments",
        ("assignment_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignment_grades.submission_id→submissions",
        "assignment_grades",
        "assignment_submissions",
        ("submission_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignment_grades.assignment_id→assignments",
        "assignment_grades",
        "assignments",
        ("assignment_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignment_grade_scores.grade_id→grades",
        "assignment_grade_scores",
        "assignment_grades",
        ("grade_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "assignment_grade_scores.criterion_id→criteria",
        "assignment_grade_scores",
        "assignment_criteria",
        ("criterion_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "lesson_progress.user_sub→users",
        "lesson_progress",
        "users",
        ("user_sub",),
        ("user_sub",),
    ),
    ForeignKeyEdge(
        "lesson_progress.(course_id,lesson_id)→lessons",
        "lesson_progress",
        "lessons",
        ("course_id", "lesson_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "lesson_progress.course_id→courses",
        "lesson_progress",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "lesson_notes.user_sub→users",
        "lesson_notes",
        "users",
        ("user_sub",),
        ("user_sub",),
    ),
    ForeignKeyEdge(
        "lesson_notes.(course_id,lesson_id)→lessons",
        "lesson_notes",
        "lessons",
        ("course_id", "lesson_id"),
        ("course_id", "id"),
    ),
    ForeignKeyEdge(
        "learning_activity_days.user_sub→users",
        "learning_activity_days",
        "users",
        ("user_sub",),
        ("user_sub",),
    ),
    ForeignKeyEdge(
        "research_team_required_courses.course_id→courses",
        "research_team_required_courses",
        "courses",
        ("course_id",),
        ("id",),
    ),
    ForeignKeyEdge(
        "purchases.user_sub→users",
        "purchases",
        "users",
        ("user_sub",),
        ("user_sub",),
    ),
    ForeignKeyEdge(
        "purchases.course_id→courses",
        "purchases",
        "courses",
        ("course_id",),
        ("id",),
        require_non_null=("course_id",),
    ),
    ForeignKeyEdge(
        "certificates.course_id→courses",
        "certificates",
        "courses",
        ("course_id",),
        ("id",),
    ),
)


def pairs_matching_schema() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for edge in DSQL_FOREIGN_KEY_EDGES:
        pairs.update(edge.parent_pairs_6_1())
    return pairs


def assert_sql_uses_left_join_is_null(sql: str) -> None:
    lowered = sql.lower()
    assert "left join" in lowered and " is null" in lowered
