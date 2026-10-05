"""RS-16 seed SQL generator: one statement each, quoted text, idempotent inserts."""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from services.certificates.models import CREDENTIAL_ID_RE

_HEX6 = re.compile(r"^[0-9A-F]{6}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _generator_path() -> Path:
    return _repo_root() / "scripts" / "rs16-seed" / "build_seed_sql.py"


def _load_generator():
    path = _generator_path()
    assert path.is_file(), f"missing seed SQL generator {path}"
    spec = importlib.util.spec_from_file_location("rs16_build_seed_sql", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _one_statement(sql: str) -> None:
    parts = [part.strip() for part in sql.split(";") if part.strip()]
    assert len(parts) == 1, sql[:80]


def test_quoting_helper_survives_apostrophes_and_dollar_quotes() -> None:
    source = _generator_path().read_text(encoding="utf-8")
    assert source.count("def sql_literal") == 1
    assert re.search(r"(?<![A-Za-z0-9_])f[\"']", source) is None

    gen = _load_generator()
    quoted = gen.sql_literal("it's $$ money")
    assert quoted == "'it''s $$ money'"
    assert "$$" in gen.sql_literal("keep $$ intact")
    assert gen.sql_literal("plain") == "'plain'"


def test_each_statement_is_single_and_inserts_are_guarded() -> None:
    gen = _load_generator()
    doc = gen.load_seed_document()
    statements = gen.build_seed_statements(doc)
    assert statements
    kinds = [stmt.kind for stmt in statements]
    assert kinds.count("course") == 4
    assert "unpublish_igcse" in kinds
    assert "purchase" in kinds
    assert "progress" in kinds
    assert "certificate" in kinds

    joined = "\n".join(stmt.sql for stmt in statements)
    assert "INSERT INTO bundle_offers" not in joined
    assert "UPDATE bundle_offers" not in joined
    assert "wipe_catalog" not in joined
    assert "DELETE FROM courses" not in joined

    for stmt in statements:
        _one_statement(stmt.sql)
        if stmt.sql.lstrip().upper().startswith("INSERT"):
            assert "NOT EXISTS" in stmt.sql

    igcse = next(stmt for stmt in statements if stmt.kind == "unpublish_igcse")
    assert "IGCSE Computer Science" in igcse.sql
    assert "DRAFT" in igcse.sql


def test_lesson_rows_are_pending_with_empty_video_and_ordered() -> None:
    gen = _load_generator()
    doc = gen.load_seed_document()
    statements = gen.build_seed_statements(doc)
    lessons = [stmt for stmt in statements if stmt.kind == "lesson"]
    assert lessons

    for course in doc["courses"]:
        course_lessons = [
            stmt for stmt in lessons if stmt.course_title == course["title"]
        ]
        expected = [
            (module_index, lesson_index, lesson_title)
            for module_index, module in enumerate(course["modules"])
            for lesson_index, lesson_title in enumerate(module["lessons"])
        ]
        assert len(course_lessons) == len(expected)
        for stmt, (module_index, lesson_index, lesson_title) in zip(
            course_lessons, expected, strict=True
        ):
            assert stmt.module_order == module_index
            assert stmt.lesson_order == lesson_index
            assert gen.sql_literal(lesson_title) in stmt.sql
            fragment = (
                ", "
                + str(lesson_index)
                + ", '', 'pending', 0 FROM"
            )
            assert fragment in stmt.sql

    fisher = next(stmt for stmt in lessons if "Fisher" in stmt.sql)
    assert "Fisher''s Exact Test" in fisher.sql
    assert "Fisher's Exact Test" not in fisher.sql


def test_module_order_and_certificate_id_shape() -> None:
    gen = _load_generator()
    doc = gen.load_seed_document()
    statements = gen.build_seed_statements(doc)
    codes = [course["certificateCode"] for course in doc["courses"]]
    assert len(set(codes)) == 4
    for code in codes:
        assert _HEX6.match(code)

    for course in doc["courses"]:
        modules = [
            stmt
            for stmt in statements
            if stmt.kind == "module" and stmt.course_title == course["title"]
        ]
        assert len(modules) == len(course["modules"])
        for index, (stmt, module) in enumerate(zip(modules, course["modules"], strict=True)):
            assert stmt.module_order == index
            assert gen.sql_literal(module["title"]) in stmt.sql
            assert "AND m.module_order = " + str(index) in stmt.sql

    credential_id = gen.seed_credential_id(doc)
    assert CREDENTIAL_ID_RE.match(credential_id)
    assert credential_id.startswith("RS-" + doc["courses"][0]["certificateCode"] + "-")
    assert credential_id.endswith("-" + doc["certificate"]["suffix"])

    certificate_sql = next(stmt.sql for stmt in statements if stmt.kind == "certificate")
    assert doc["certificate"]["suffix"] in certificate_sql
    assert "btrim(c.certificate_code)" in certificate_sql
    assert "valid" in certificate_sql

    purchase_sql = next(stmt.sql for stmt in statements if stmt.kind == "purchase")
    assert "rs16-seed-ci-student" in purchase_sql
    assert "bundle_offers" in purchase_sql
    assert "'bundle'" in purchase_sql
    assert "'paid'" in purchase_sql
    assert "'prod'" in purchase_sql

    joined = "\n".join(stmt.sql for stmt in statements)
    assert "ORDER BY created_at DESC LIMIT 1" in joined
    assert "ORDER BY created_at LIMIT 1" not in joined
