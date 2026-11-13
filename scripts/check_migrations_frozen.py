"""Fail CI when infrastructure/database/migrations/ diverges from the frozen allowlist (DSQL-0)."""

from __future__ import annotations

import sys
from pathlib import Path

MIGRATIONS_DIR = Path("infrastructure") / "database" / "migrations"

# §5.1 — frozen set (24 files). No 005_*.sql by design.
ALLOWLIST: frozenset[str] = frozenset(
    {
        "001_initial_schema.sql",
        "002_add_course_modules.sql",
        "003_progress_course_lesson_fk.sql",
        "004_enforce_course_created_by.sql",
        "006_question_banks_module_quizzes.sql",
        "007_question_bank_questions.sql",
        "008_student_module_quiz_bindings.sql",
        "009_module_quiz_attempts.sql",
        "010_module_quiz_attempt_submissions.sql",
        "011_billing_subscription.sql",
        "012_billing_plan_price_50_jod.sql",
        "013_student_active_session.sql",
        "014_rate_limit_counters.sql",
        "015_one_time_purchases.sql",
        "016_user_profile_fields.sql",
        "017_course_page_content.sql",
        "018_module_quiz_pass_percent.sql",
        "019_lesson_files_and_notes.sql",
        "020_assignments.sql",
        "021_certificates.sql",
        "022_research_team.sql",
        "023_rs16_learning_features.sql",
        "024_hyperpay_jod.sql",
        "025_bundle_certificates.sql",
    }
)


def unexpected_migration_files(root: Path) -> list[str]:
    """Return migration basenames that are extra on disk or missing from the allowlist."""
    migrations_dir = root / MIGRATIONS_DIR
    on_disk = (
        {p.name for p in migrations_dir.glob("*.sql")}
        if migrations_dir.is_dir()
        else set()
    )
    extra = on_disk - ALLOWLIST
    missing = ALLOWLIST - on_disk
    return sorted(extra | missing)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    offenders = unexpected_migration_files(repo_root)
    if offenders:
        for name in offenders:
            print(name, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
