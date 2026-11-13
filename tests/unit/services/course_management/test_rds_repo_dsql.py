"""DSQL-3 S2: course catalog RDS adapter OCC, tombstone reads, batched deletes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple
from unittest.mock import patch

import pytest


_DELETING_SUBSTR = "deleting"


class _PgError(Exception):
    def __init__(self, pgcode: str, *, message: str = "err") -> None:
        super().__init__(message)
        self.pgcode = pgcode
        self.diag: Any = None


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    bulk_rows_to_return: Optional[List[Tuple[Any, ...]]] = None
    rowcount: int = 0
    _execute_hook: Any = None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        if self._execute_hook is not None:
            self._execute_hook(sql, params)
            return
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        if self.bulk_rows_to_return is not None:
            out = self.bulk_rows_to_return
            self.bulk_rows_to_return = None
            return out
        out = list(self.rows_to_return)
        self.rows_to_return.clear()
        return out

    def close(self) -> None:
        pass

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0
    autocommit: bool = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


def _repo(conn: FakeConn):
    from services.course_management.rds_repo import CourseCatalogRdsRepository

    return CourseCatalogRdsRepository(lambda: conn)


def _course_row(*, status: str = "DRAFT") -> Tuple[Any, ...]:
    cid = uuid.UUID("11111111-2222-3333-4444-555555555555")
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    return (cid, "T", "D", status, "owner", "", now, now, None, {}, "ABCDEF")


class TestDeletingReadFilter:
    def test_list_courses_sql_excludes_deleting(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.bulk_rows_to_return = []
        _repo(conn).list_courses()
        sql, _ = conn.cursor_obj.executions[0]
        assert _DELETING_SUBSTR in sql.lower()
        assert "<>" in sql or "is null" in sql.lower()

    def test_list_courses_by_instructor_excludes_deleting(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.bulk_rows_to_return = []
        _repo(conn).list_courses_by_instructor("teacher")
        sql, _ = conn.cursor_obj.executions[-1]
        assert _DELETING_SUBSTR in sql.lower()

    def test_get_course_default_excludes_deleting(self) -> None:
        conn = FakeConn()
        _repo(conn).get_course("cid-1")
        sql, _ = conn.cursor_obj.executions[-1]
        assert _DELETING_SUBSTR in sql.lower()

    def test_get_course_include_deleting_omits_filter(self) -> None:
        conn = FakeConn()
        _repo(conn).get_course("cid-1", include_deleting=True)
        sql, _ = conn.cursor_obj.executions[-1]
        assert _DELETING_SUBSTR not in sql.lower()


class TestCreateCourseOcc:
    def test_certificate_insert_retries_40001_inside_transaction(self) -> None:
        conn = FakeConn()
        new_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        conn.cursor_obj.rows_to_return.append(
            (new_id, "T", "D", "DRAFT", "c", "", now, now, None, {}, "ABCDEF")
        )
        calls = {"n": 0}

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.executions.append((sql, tuple(params)))
            if "INSERT INTO COURSES" in sql.upper():
                calls["n"] += 1
                if calls["n"] == 1:
                    raise _PgError("40001", message="serialization failure")

        conn.cursor_obj._execute_hook = hook
        course = _repo(conn).create_course("T", "D", created_by="c")
        assert course.title == "T"
        course_inserts = [
            p
            for s, p in conn.cursor_obj.executions
            if "INSERT INTO COURSES" in s.upper()
        ]
        assert len(course_inserts) >= 2

    def test_certificate_unique_violation_draws_new_code(self) -> None:
        conn = FakeConn()
        new_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        conn.cursor_obj.rows_to_return.append(
            (new_id, "T", "D", "DRAFT", "c", "", now, now, None, {}, "BBBBBB")
        )
        codes = iter(["AAAAAA", "BBBBBB"])

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.executions.append((sql, tuple(params)))
            if "INSERT INTO COURSES" in sql.upper():
                cert = params[4] if len(params) > 4 else ""
                if cert == "AAAAAA":
                    err = _PgError("23505", message="duplicate certificate_code")
                    err.diag = type(
                        "D",
                        (),
                        {
                            "constraint_name": "courses_certificate_code_key",
                            "column_name": "certificate_code",
                        },
                    )()
                    raise err

        conn.cursor_obj._execute_hook = hook
        with patch(
            "services.course_management.rds_repo.generate_certificate_code",
            side_effect=lambda **_: next(codes),
        ):
            course = _repo(conn).create_course("T", "D", created_by="c")
        assert course.certificateCode == "BBBBBB"
        cert_params = [
            p[4]
            for s, p in conn.cursor_obj.executions
            if "INSERT INTO COURSES" in s.upper() and len(p) > 4
        ]
        assert cert_params[:2] == ["AAAAAA", "BBBBBB"]


class TestModuleLessonInsertOcc:
    def test_create_course_module_single_transaction_max_then_insert(self) -> None:
        conn = FakeConn()
        mid = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        conn.cursor_obj.rows_to_return.extend([(1,), (mid, "c", "M", "", 2, now, now)])
        repo = _repo(conn)
        repo.create_course_module("course-id", "M")
        between_commit = conn.committed
        assert between_commit >= 1
        sqls = [s.upper() for s, _ in conn.cursor_obj.executions]
        assert any("MAX(MODULE_ORDER)" in s for s in sqls)
        assert any("INSERT INTO COURSE_MODULES" in s for s in sqls)

    def test_create_course_module_retries_23505(self) -> None:
        conn = FakeConn()
        mid = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        conn.cursor_obj.rows_to_return.extend(
            [
                (1,),
                (1,),
                (mid, "c", "M", "", 2, now, now),
            ]
        )
        attempts = {"n": 0}

        orig = conn.cursor_obj.execute

        def guarded(sql: str, params: Sequence[Any] = ()) -> None:
            if "INSERT INTO COURSE_MODULES" in sql.upper():
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise _PgError("23505", message="module_order")
            orig(sql, params)

        conn.cursor_obj.execute = guarded  # type: ignore[method-assign]
        _repo(conn).create_course_module("course-id", "M")
        assert attempts["n"] == 2

    def test_create_lesson_single_transaction_max_then_insert(self) -> None:
        conn = FakeConn()
        lid = uuid.UUID("cccccccc-dddd-eeee-ffff-000000000001")
        mid = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        conn.cursor_obj.rows_to_return.extend(
            [
                (2,),
                (lid,),
                (lid, "L", 3, "", "pending", "", 0, mid, 0, ""),
            ]
        )
        _repo(conn).create_lesson("course-id", str(mid), "L")
        sqls = " ".join(s.upper() for s, _ in conn.cursor_obj.executions)
        assert "MAX(LESSON_ORDER)" in sqls
        assert "INSERT INTO LESSONS" in sqls


class TestSetLessonOrdersTwoPhase:
    def test_rejects_more_than_1000_lessons(self) -> None:
        conn = FakeConn()
        orders = {f"l{i}": i for i in range(1001)}
        with pytest.raises(ValueError, match="1000"):
            _repo(conn).set_lesson_orders("course-id", orders)

    def test_negative_temporary_order_before_final(self) -> None:
        conn = FakeConn()
        orders = {"l1": 2, "l2": 1}
        _repo(conn).set_lesson_orders("course-id", orders)
        updates = [
            (params[0], params[2])
            for sql, params in conn.cursor_obj.executions
            if sql.upper().startswith("UPDATE")
        ]
        assert len(updates) == 4
        by_lesson: dict[str, list[int]] = {}
        for order_val, lid in updates:
            by_lesson.setdefault(str(lid), []).append(int(order_val))
        for seq in by_lesson.values():
            assert seq[0] < 0
            assert seq[1] > 0


class TestBatchedCatalogDeletes:
    def test_delete_lesson_files_for_course_uses_limit_1000(self) -> None:
        conn = FakeConn()
        calls = {"n": 0}

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.executions.append((sql, tuple(params)))
            calls["n"] += 1
            conn.cursor_obj.rowcount = 500 if calls["n"] == 1 else 0

        conn.cursor_obj._execute_hook = hook
        total = _repo(conn).delete_lesson_files_for_course("course-id")
        assert total == 500
        sql, params = conn.cursor_obj.executions[0]
        assert "lesson_files" in sql.lower()
        assert "limit 1000" in sql.lower()
        assert "course-id" in params

    def test_delete_course_row_sql(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rowcount = 1

        def hook(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.executions.append((sql, tuple(params)))
            conn.cursor_obj.rowcount = 1

        conn.cursor_obj._execute_hook = hook
        count = _repo(conn).delete_course_row("course-id")
        assert count == 1
        sql, params = conn.cursor_obj.executions[-1]
        assert "DELETE FROM COURSES" in sql.upper()
        assert params == ("course-id",)


class TestPurchaseGuardAndTombstone:
    def test_course_has_purchase_select_limit_1(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [(1,)]
        assert _repo(conn).course_has_purchase("course-id") is True
        sql, params = conn.cursor_obj.executions[-1]
        assert "purchases" in sql.lower()
        assert "limit 1" in sql.lower()
        assert params == ("course-id",)

    def test_set_course_status_can_set_deleting(self) -> None:
        conn = FakeConn()
        _repo(conn).set_course_status("course-id", "deleting")
        sql, params = conn.cursor_obj.executions[-1]
        assert "deleting" in params
