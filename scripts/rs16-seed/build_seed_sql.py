"""Build idempotent single-statement SQL for the RS-16 course seed.

String values go through sql_literal only. Content is concatenated, not
interpolated with format strings.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_CATALOG = Path(__file__).resolve().parents[2] / "infrastructure" / "lambda" / "catalog"
if str(_CATALOG) not in sys.path:
    sys.path.insert(0, str(_CATALOG))

from services.course_management.course_page_validation import (  # noqa: E402
    validate_and_normalize_course_page,
)

_SEED_DIR = Path(__file__).resolve().parent
_HEX = "0123456789ABCDEF"


class SeedStatement:
    def __init__(
        self,
        kind: str,
        sql: str,
        *,
        course_title: str | None = None,
        module_order: int | None = None,
        lesson_order: int | None = None,
    ) -> None:
        if ";" in sql:
            raise ValueError("seed SQL must be one statement and must not contain ';'")
        self.kind = kind
        self.sql = sql
        self.course_title = course_title
        self.module_order = module_order
        self.lesson_order = lesson_order


def sql_literal(value: str) -> str:
    """Quote a SQL string literal. Apostrophes are doubled; dollar quotes stay data."""
    if not isinstance(value, str):
        raise TypeError("sql_literal expects a string")
    return "'" + value.replace("'", "''") + "'"


def sql_int(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("sql_int expects an int")
    return str(value)


def load_seed_document(path: Path | None = None) -> dict:
    target = path if path is not None else _SEED_DIR / "courses.json"
    return json.loads(target.read_text(encoding="utf-8"))


def seed_credential_id(doc: dict, *, year: int | None = None) -> str:
    """Public id RS-{certificate_code}-{UTC year}-{10 hex} for the seeded certificate."""
    cert = doc["certificate"]
    course = _course_by_title(doc, cert["courseTitle"])
    code = _require_hex(course["certificateCode"], 6, "certificateCode")
    suffix = _require_hex(cert["suffix"], 10, "suffix")
    utc_year = datetime.now(timezone.utc).year if year is None else year
    if isinstance(utc_year, bool) or not isinstance(utc_year, int):
        raise TypeError("year must be an int")
    return "RS-" + code + "-" + sql_int(utc_year) + "-" + suffix


def build_seed_statements(doc: dict) -> list[SeedStatement]:
    teacher_email = doc["teacherEmail"]
    student_email = doc["studentEmail"]
    statements: list[SeedStatement] = []
    for course in doc["courses"]:
        statements.append(_course_insert(course, teacher_email))
        for module_order, module in enumerate(course["modules"]):
            statements.append(
                _module_insert(course["title"], module, module_order)
            )
            for lesson_order, lesson_title in enumerate(module["lessons"]):
                statements.append(
                    _lesson_insert(
                        course["title"],
                        module_order,
                        lesson_title,
                        lesson_order,
                    )
                )
    statements.append(_unpublish_igcse(doc["igcseTitle"]))
    statements.append(_purchase_insert(doc, student_email))
    statements.append(_progress_insert(doc, student_email))
    statements.append(_certificate_insert(doc, student_email))
    return statements


def write_statement_files(dest: Path, doc: dict | None = None) -> int:
    """Write one .sql file per statement plus a manifest of index and kind only."""
    document = doc if doc is not None else load_seed_document()
    statements = build_seed_statements(document)
    dest.mkdir(parents=True, exist_ok=True)
    manifest = []
    for index, stmt in enumerate(statements, start=1):
        name = str(index).zfill(4) + ".sql"
        (dest / name).write_text(stmt.sql, encoding="utf-8")
        manifest.append({"index": index, "kind": stmt.kind, "file": name})
    (dest / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return len(statements)


def _course_by_title(doc: dict, title: str) -> dict:
    for course in doc["courses"]:
        if course["title"] == title:
            return course
    raise KeyError("certificate course is not in the seed document")


def _require_hex(value: str, size: int, field: str) -> str:
    if not isinstance(value, str) or len(value) != size:
        raise ValueError(field + " must be " + str(size) + " hex characters")
    upper = value.upper()
    for char in upper:
        if char not in _HEX:
            raise ValueError(field + " must be uppercase hex")
    return upper


def _user_subquery(email: str, columns: str) -> str:
    return (
        "(SELECT "
        + columns
        + " FROM users WHERE email = "
        + sql_literal(email)
        + " ORDER BY created_at DESC LIMIT 1)"
    )


def _course_insert(course: dict, teacher_email: str) -> SeedStatement:
    page = validate_and_normalize_course_page(course["pageContent"])
    page_json = json.dumps(page, ensure_ascii=False, separators=(",", ":"))
    code = _require_hex(course["certificateCode"], 6, "certificateCode")
    sql = (
        "INSERT INTO courses ("
        "title, description, status, created_by, price_amount_minor, "
        "page_content, certificate_code) SELECT "
        + sql_literal(course["title"])
        + ", "
        + sql_literal(course["description"])
        + ", "
        + sql_literal("PUBLISHED")
        + ", u.user_sub, "
        + sql_int(course["priceAmountMinor"])
        + ", "
        + sql_literal(page_json)
        + "::jsonb, "
        + sql_literal(code)
        + " FROM "
        + _user_subquery(teacher_email, "user_sub")
        + " u WHERE NOT EXISTS (SELECT 1 FROM courses c WHERE c.title = "
        + sql_literal(course["title"])
        + ")"
    )
    return SeedStatement("course", sql, course_title=course["title"])


def _module_insert(course_title: str, module: dict, module_order: int) -> SeedStatement:
    sql = (
        "INSERT INTO course_modules (course_id, title, description, module_order) "
        "SELECT c.id, "
        + sql_literal(module["title"])
        + ", "
        + sql_literal(module.get("description") or "")
        + ", "
        + sql_int(module_order)
        + " FROM courses c WHERE c.title = "
        + sql_literal(course_title)
        + " AND NOT EXISTS (SELECT 1 FROM course_modules m "
        "WHERE m.course_id = c.id AND m.module_order = "
        + sql_int(module_order)
        + ")"
    )
    return SeedStatement(
        "module",
        sql,
        course_title=course_title,
        module_order=module_order,
    )


def _lesson_insert(
    course_title: str,
    module_order: int,
    lesson_title: str,
    lesson_order: int,
) -> SeedStatement:
    sql = (
        "INSERT INTO lessons ("
        "course_id, module_id, title, lesson_order, video_key, video_status, duration) "
        "SELECT c.id, m.id, "
        + sql_literal(lesson_title)
        + ", "
        + sql_int(lesson_order)
        + ", "
        + sql_literal("")
        + ", "
        + sql_literal("pending")
        + ", 0 FROM courses c "
        "JOIN course_modules m ON m.course_id = c.id AND m.module_order = "
        + sql_int(module_order)
        + " WHERE c.title = "
        + sql_literal(course_title)
        + " AND NOT EXISTS (SELECT 1 FROM lessons l "
        "WHERE l.course_id = c.id AND l.module_id = m.id AND l.lesson_order = "
        + sql_int(lesson_order)
        + ")"
    )
    return SeedStatement(
        "lesson",
        sql,
        course_title=course_title,
        module_order=module_order,
        lesson_order=lesson_order,
    )


def _unpublish_igcse(title: str) -> SeedStatement:
    sql = (
        "UPDATE courses SET status = "
        + sql_literal("DRAFT")
        + ", updated_at = NOW() WHERE title = "
        + sql_literal(title)
        + " AND status IS DISTINCT FROM "
        + sql_literal("DRAFT")
    )
    return SeedStatement("unpublish_igcse", sql)


def _purchase_insert(doc: dict, student_email: str) -> SeedStatement:
    purchase = doc["purchase"]
    sql = (
        "INSERT INTO purchases ("
        "user_sub, environment, product_type, course_id, status, "
        "amount_minor, currency, provider, provider_tran_ref) "
        "SELECT u.user_sub, "
        + sql_literal(purchase["environment"])
        + ", "
        + sql_literal(purchase["productType"])
        + ", NULL, "
        + sql_literal(purchase["status"])
        + ", b.amount_minor, b.currency, "
        + sql_literal(purchase["provider"])
        + ", "
        + sql_literal(purchase["providerTranRef"])
        + " FROM "
        + _user_subquery(student_email, "user_sub")
        + " u JOIN bundle_offers b ON b.environment = "
        + sql_literal(purchase["environment"])
        + " WHERE NOT EXISTS (SELECT 1 FROM purchases p "
        "WHERE p.user_sub = u.user_sub AND p.environment = "
        + sql_literal(purchase["environment"])
        + " AND p.product_type = "
        + sql_literal(purchase["productType"])
        + " AND p.status = "
        + sql_literal("paid")
        + ")"
    )
    return SeedStatement("purchase", sql)


def _progress_insert(doc: dict, student_email: str) -> SeedStatement:
    course_title = doc["certificate"]["courseTitle"]
    limit = doc["progressLessonCount"]
    sql = (
        "INSERT INTO lesson_progress ("
        "user_sub, lesson_id, course_id, completed, completed_at, last_position_sec) "
        "SELECT u.user_sub, l.id, c.id, TRUE, NOW(), 0 FROM "
        + _user_subquery(student_email, "user_sub")
        + " u JOIN courses c ON c.title = "
        + sql_literal(course_title)
        + " JOIN course_modules m ON m.course_id = c.id AND m.module_order = 0 "
        "JOIN lessons l ON l.course_id = c.id AND l.module_id = m.id "
        "AND l.lesson_order < "
        + sql_int(limit)
        + " WHERE NOT EXISTS (SELECT 1 FROM lesson_progress lp "
        "WHERE lp.user_sub = u.user_sub AND lp.lesson_id = l.id)"
    )
    return SeedStatement("progress", sql, course_title=course_title)


def _certificate_insert(doc: dict, student_email: str) -> SeedStatement:
    cert = doc["certificate"]
    suffix = _require_hex(cert["suffix"], 10, "suffix")
    sql = (
        "INSERT INTO certificates ("
        "user_sub, course_id, credential_id, student_name, course_title, "
        "issue_date, instructor_name, instructor_title, status) "
        "SELECT u.user_sub, c.id, "
        "'RS-' || btrim(c.certificate_code) || '-' || "
        "to_char((NOW() AT TIME ZONE 'UTC'), 'YYYY') || '-' || "
        + sql_literal(suffix)
        + ", COALESCE(NULLIF(btrim(concat_ws(' ', u.given_name, u.family_name)), ''), "
        + sql_literal(cert["fallbackStudentName"])
        + "), c.title, (NOW() AT TIME ZONE 'UTC')::date, "
        + sql_literal(cert["instructorName"])
        + ", "
        + sql_literal(cert["instructorTitle"])
        + ", "
        + sql_literal("valid")
        + " FROM "
        + _user_subquery(student_email, "user_sub, given_name, family_name")
        + " u JOIN courses c ON c.title = "
        + sql_literal(cert["courseTitle"])
        + " WHERE NOT EXISTS (SELECT 1 FROM certificates cert "
        "WHERE cert.user_sub = u.user_sub AND cert.course_id = c.id)"
    )
    return SeedStatement("certificate", sql, course_title=cert["courseTitle"])


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_seed_sql.py <output-dir>")
    count = write_statement_files(Path(sys.argv[1]))
    print("statements " + str(count))


if __name__ == "__main__":
    main()
