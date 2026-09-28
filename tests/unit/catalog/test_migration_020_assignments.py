"""RS-13: migration 020 assignments tables and constraints."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_MIGRATION = (
    _ROOT
    / "infrastructure"
    / "database"
    / "migrations"
    / "020_assignments.sql"
)


def test_migration_020_file_exists() -> None:
    assert _MIGRATION.is_file(), f"missing migration: {_MIGRATION}"


def test_migration_020_assignments_ddl() -> None:
    sql = _MIGRATION.read_text(encoding="utf-8")
    lowered = sql.lower()
    compact = " ".join(lowered.split())

    assert "create table" in lowered and "assignments" in lowered
    assert "create table" in lowered and "assignment_criteria" in lowered
    assert "create table" in lowered and "assignment_submissions" in lowered
    assert "create table" in lowered and "assignment_submission_files" in lowered
    assert "create table" in lowered and "assignment_grades" in lowered
    assert "create table" in lowered and "assignment_grade_scores" in lowered

    assert "module_id" in lowered
    assert "course_id" in lowered
    assert "counts_toward_certificate" in lowered
    assert "instructions_image_key" in lowered
    assert "rubric_image_key" in lowered
    assert "pass_percent" in lowered
    assert "instructions_mode" in lowered
    assert "rubric_mode" in lowered

    assert "references courses(id) on delete cascade" in compact or (
        "references courses (id) on delete cascade" in compact
    )
    assert "references course_modules" in lowered
    assert "references assignments(id) on delete cascade" in compact or (
        "references assignments (id) on delete cascade" in compact
    )

    assert "assignment_submissions_one_draft_per_user" in lowered
    assert "where status = 'draft'" in compact
    assert "unique index" in lowered and "draft" in lowered

    # No document-handout table; certificate uniqueness must not exist.
    assert "handout" not in lowered
    assert "unique" not in compact or "counts_toward_certificate" not in (
        compact[compact.find("unique") : compact.find("unique") + 80]
        if "unique" in compact
        else ""
    )
