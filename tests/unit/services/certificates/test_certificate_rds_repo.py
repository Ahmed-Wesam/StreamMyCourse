"""DSQL-7b S2: certificate repo OCC and idempotent inserts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.certificates.ports import BundleCertificateRow, CertificateRow
from services.certificates.rds_repo import CertificatesRdsRepository


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    rowcount: int = 1
    _execute_impl: Any = None

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        if self._execute_impl is not None:
            self._execute_impl(self, sql, params)
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)


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


def _cert_row(*, status: str = "valid") -> CertificateRow:
    return CertificateRow(
        id="cert-1",
        user_sub="student-1",
        course_id="course-1",
        credential_id="RS-ABCDEF-2026-0123456789",
        student_name="Ada Lovelace",
        course_title="Research Methodology",
        issue_date=date(2026, 1, 1),
        instructor_name="Dr. Test",
        instructor_title="Instructor",
        status=status,
    )


def _bundle_row(*, status: str = "valid") -> BundleCertificateRow:
    return BundleCertificateRow(
        id="bundle-1",
        user_sub="student-1",
        credential_id="RS-B00001-2026-0123456789",
        student_name="Ada Lovelace",
        issue_date=date(2026, 1, 1),
        instructor_name="Dr. Test",
        instructor_title="Instructor",
        status=status,
    )


def _course_db_tuple(status: str = "valid") -> Tuple[Any, ...]:
    return (
        "cert-1",
        "student-1",
        "course-1",
        "RS-ABCDEF-2026-0123456789",
        "Ada Lovelace",
        "Research Methodology",
        date(2026, 1, 1),
        "Dr. Test",
        "Instructor",
        status,
        None,
        None,
    )


class TestCertificateInsertOcc:
    def test_insert_certificate_sql_has_on_conflict(self) -> None:
        fake = FakeConn()
        fake.cursor_obj.rows_to_return = [_course_db_tuple()]
        repo = CertificatesRdsRepository(lambda: fake)
        repo.insert_certificate(_cert_row())
        sql = " ".join(fake.cursor_obj.executions[0][0].lower().split())
        assert "on conflict (user_sub, course_id) do nothing" in sql

    def test_second_insert_returns_existing_revoked_row(self) -> None:
        fake = FakeConn()
        fake.cursor_obj.rows_to_return = [None, _course_db_tuple("revoked")]
        repo = CertificatesRdsRepository(lambda: fake)
        out = repo.insert_certificate(_cert_row())
        assert out.status == "revoked"
        assert len(fake.cursor_obj.executions) == 2
        assert "SELECT" in fake.cursor_obj.executions[1][0].upper()

    def test_insert_certificate_retries_40001_once(self) -> None:
        fake = FakeConn()
        fake.cursor_obj.rows_to_return = [_course_db_tuple(), _course_db_tuple()]
        attempts = {"n": 0}
        original = fake.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            original(sql, params)
            if "INSERT INTO certificates" in sql:
                attempts["n"] += 1
                if attempts["n"] == 1:
                    err = Exception("serialization failure")
                    err.pgcode = "40001"  # type: ignore[attr-defined]
                    raise err

        fake.cursor_obj.execute = execute  # type: ignore[method-assign]
        repo = CertificatesRdsRepository(lambda: fake)
        repo.insert_certificate(_cert_row())
        assert attempts["n"] == 2
        assert fake.rolled_back == 1
        assert fake.committed == 1

    def test_bundle_insert_has_on_conflict_user_sub(self) -> None:
        fake = FakeConn()
        fake.cursor_obj.rows_to_return = [
            (
                "bundle-1",
                "student-1",
                "RS-B00001-2026-0123456789",
                "Ada Lovelace",
                date(2026, 1, 1),
                "Dr. Test",
                "Instructor",
                "valid",
                None,
                None,
            )
        ]
        repo = CertificatesRdsRepository(lambda: fake)
        repo.insert_bundle_certificate(_bundle_row())
        sql = " ".join(fake.cursor_obj.executions[0][0].lower().split())
        assert "on conflict (user_sub) do nothing" in sql

    def test_revoke_retries_40001_once(self) -> None:
        fake = FakeConn()
        fake.cursor_obj.rows_to_return = [_course_db_tuple("revoked"), _course_db_tuple("revoked")]
        updates = {"n": 0}
        original = fake.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            original(sql, params)
            if "UPDATE certificates" in sql:
                updates["n"] += 1
                if updates["n"] == 1:
                    err = Exception("serialization failure")
                    err.pgcode = "40001"  # type: ignore[attr-defined]
                    raise err

        fake.cursor_obj.execute = execute  # type: ignore[method-assign]
        repo = CertificatesRdsRepository(lambda: fake)
        repo.revoke(
            "cert-1",
            revoked_by="teacher-1",
            revoked_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        assert updates["n"] == 2
        assert fake.committed == 1
