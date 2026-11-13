"""Parse checks for Aurora DSQL bootstrap schema (plans/dsql-ws1-foundation.md §6)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA = _ROOT / "infrastructure" / "database" / "dsql" / "0001_schema.sql"

TABLES_6_1 = frozenset(
    {
        "schema_migrations",
        "users",
        "courses",
        "course_modules",
        "lessons",
        "lesson_files",
        "question_banks",
        "questions",
        "module_quizzes",
        "assignment_criteria",
        "assignments",
        "assignment_submission_files",
        "assignment_grades",
        "assignment_grade_scores",
        "research_team_required_courses",
        "bundle_offers",
        "rate_limit_counters",
        "payment_webhook_events",
        "enrollments",
        "lesson_progress",
        "lesson_notes",
        "learning_activity_days",
        "student_module_quiz_bindings",
        "student_module_quiz_binding_questions",
        "module_quiz_attempts",
        "module_quiz_attempt_submissions",
        "assignment_submissions",
        "purchases",
        "certificates",
        "bundle_certificates",
        "research_team_applications",
    }
)

RETIRED_TABLES = frozenset(
    {"subscription_plans", "user_subscriptions", "teacher_merchant_accounts"}
)

FORBIDDEN_PATTERNS = (
    "uuid-ossp",
    "uuid_generate_v4",
    "DO $$",
    "TEXT[]",
    "CREATE EXTENSION",
)


@pytest.fixture(scope="module")
def schema_sql() -> str:
    assert _SCHEMA.is_file(), f"missing {_SCHEMA}"
    return _SCHEMA.read_text(encoding="utf-8")


def _created_tables(sql: str) -> set[str]:
    found: set[str] = set()
    for match in re.finditer(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?app\.(\w+)",
        sql,
        re.IGNORECASE,
    ):
        found.add(match.group(1))
    return found


def test_all_ownership_tables_present(schema_sql: str) -> None:
    tables = _created_tables(schema_sql)
    missing = TABLES_6_1 - tables
    assert not missing, f"missing tables: {sorted(missing)}"


def test_retired_tables_absent(schema_sql: str) -> None:
    for name in RETIRED_TABLES:
        assert not re.search(
            rf"CREATE\s+TABLE\s+app\.{name}\b",
            schema_sql,
            re.IGNORECASE,
        ), f"retired table {name} must not be created"


def test_forbidden_patterns_absent(schema_sql: str) -> None:
    for pattern in FORBIDDEN_PATTERNS:
        assert pattern not in schema_sql, f"forbidden pattern {pattern!r}"


def test_secondary_indexes_are_async(schema_sql: str) -> None:
    for match in re.finditer(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?!ASYNC)(\S+)",
        schema_sql,
        re.IGNORECASE,
    ):
        name = match.group(1)
        if name.upper() == "ASYNC":
            continue
        pytest.fail(f"index {name} is not CREATE INDEX ASYNC")


def test_jsonb_tag_columns(schema_sql: str) -> None:
    assert re.search(
        r"research_interest_tags\s+JSONB",
        schema_sql,
        re.IGNORECASE,
    ), "users.research_interest_tags must be JSONB"
    assert re.search(
        r"research_areas\s+JSONB",
        schema_sql,
        re.IGNORECASE,
    ), "research_team_applications.research_areas must be JSONB"


def test_column_checklists(schema_sql: str) -> None:
    checks = [
        ("users", "student_active_session_id"),
        ("users", "pref_autoplay_next"),
        ("users", "pref_auto_mark_complete"),
        ("users", "pref_progress_celebrations"),
        ("users", "research_interest_tags"),
        ("users", "last_login_at"),
        ("courses", "page_content"),
        ("courses", "price_amount_minor"),
        ("courses", "certificate_code"),
        ("lessons", "transcript"),
        ("module_quizzes", "pass_percent"),
        ("module_quizzes", "served_count_n"),
        ("questions", "options_json"),
        ("purchases", "product_type"),
        ("purchases", "purchases_amount_minor_whole_jod"),
    ]
    for table, column in checks:
        pattern = rf"CREATE\s+TABLE\s+app\.{table}\b[\s\S]*?\);"
        block = re.search(pattern, schema_sql, re.IGNORECASE)
        assert block is not None, f"missing CREATE TABLE app.{table}"
        assert column in block.group(0), f"{table}.{column} missing"


def test_certificates_upper_credential_index(schema_sql: str) -> None:
    assert re.search(
        r"CREATE\s+UNIQUE\s+INDEX\s+ASYNC\s+certificates_credential_id_upper\s+ON\s+app\.certificates\s+\(\(upper\(credential_id\)\)\)",
        schema_sql,
        re.IGNORECASE,
    )


def test_module_quizzes_partial_unique_like_rds(schema_sql: str) -> None:
    assert re.search(
        r"CREATE\s+UNIQUE\s+INDEX\s+ASYNC\s+uq_module_quizzes_course_question_bank\s+ON\s+app\.module_quizzes\s+\(course_id,\s*question_bank_id\)\s+WHERE\s+question_bank_id\s+IS\s+NOT\s+NULL",
        schema_sql,
        re.IGNORECASE,
    )


def test_index_count_per_table_at_most_24(schema_sql: str) -> None:
    """Count CREATE INDEX ASYNC and inline UNIQUE/PRIMARY KEY references per table."""
    counts: dict[str, int] = {t: 0 for t in TABLES_6_1}

    for match in re.finditer(
        r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+ASYNC\s+\S+\s+ON\s+app\.(\w+)",
        schema_sql,
        re.IGNORECASE,
    ):
        counts[match.group(1)] = counts.get(match.group(1), 0) + 1

    for table in TABLES_6_1:
        block_match = re.search(
            rf"CREATE\s+TABLE\s+app\.{table}\b([\s\S]*?)\);",
            schema_sql,
            re.IGNORECASE,
        )
        if not block_match:
            continue
        block = block_match.group(1)
        counts[table] += len(re.findall(r"\bUNIQUE\b", block, re.IGNORECASE))
        counts[table] += len(re.findall(r"\bPRIMARY\s+KEY\b", block, re.IGNORECASE))

    over = {t: n for t, n in counts.items() if n > 24}
    assert not over, f"index count > 24: {over}"


def test_prod_bundle_seed_only(schema_sql: str) -> None:
    inserts = re.findall(
        r"INSERT\s+INTO\s+app\.bundle_offers[\s\S]*?;",
        schema_sql,
        re.IGNORECASE,
    )
    assert len(inserts) == 1
    assert "'prod'" in inserts[0]
    assert "'dev'" not in inserts[0]
    assert "ON CONFLICT" in inserts[0]

