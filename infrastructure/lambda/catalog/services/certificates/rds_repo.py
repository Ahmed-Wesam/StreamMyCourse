"""PostgreSQL adapter for :class:`CertificatesRepositoryPort`."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, List, Optional
from uuid import uuid4

from services.certificates.ports import CertificateRow, CertificatesRepositoryPort

try:  # pragma: no cover
    import psycopg2
    from psycopg2 import errorcodes
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]
    errorcodes = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_SELECT_COLS = """
    id, user_sub, course_id, credential_id, student_name, course_title,
    issue_date, instructor_name, instructor_title, status, revoked_at, revoked_by
"""


def _row_from_db(row: tuple) -> CertificateRow:
    return CertificateRow(
        id=str(row[0]),
        user_sub=str(row[1]),
        course_id=str(row[2]),
        credential_id=str(row[3]),
        student_name=str(row[4]),
        course_title=str(row[5]),
        issue_date=row[6],
        instructor_name=str(row[7]),
        instructor_title=str(row[8]),
        status=str(row[9]),
        revoked_at=row[10],
        revoked_by=str(row[11]) if row[11] is not None else None,
    )


class CertificatesRdsRepository(CertificatesRepositoryPort):
    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _execute(self, sql: str, params: tuple = (), *, commit: bool = False) -> Any:
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            return cur
        except Exception as exc:
            if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
                logger.warning("RDS connection lost, reconnecting: %s", exc)
                self._conn = None
                conn = self._connection()
                cur = conn.cursor()
                cur.execute(sql, params)
                if commit:
                    conn.commit()
                return cur
            conn = self._connection()
            conn.rollback()
            raise

    def _is_user_course_unique_violation(self, exc: BaseException) -> bool:
        if psycopg2 is None or errorcodes is None:
            return False
        if not isinstance(exc, psycopg2.IntegrityError):
            return False
        if getattr(exc, "pgcode", None) != errorcodes.UNIQUE_VIOLATION:
            return False
        diag = getattr(exc, "diag", None)
        constraint = str(getattr(diag, "constraint_name", "") or "").lower()
        message = str(exc).lower()
        return (
            "certificates_user_course" in constraint
            or "certificates_user_course" in message
            or "user_sub" in message
        )

    def insert_certificate(self, row: CertificateRow) -> CertificateRow:
        cert_id = row.id or str(uuid4())
        try:
            cur = self._execute(
                f"""
                INSERT INTO certificates (
                    id, user_sub, course_id, credential_id, student_name, course_title,
                    issue_date, instructor_name, instructor_title, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING {_SELECT_COLS}
                """,
                (
                    cert_id,
                    row.user_sub,
                    row.course_id,
                    row.credential_id,
                    row.student_name,
                    row.course_title,
                    row.issue_date,
                    row.instructor_name,
                    row.instructor_title,
                    row.status,
                ),
                commit=True,
            )
            fetched = cur.fetchone()
            if fetched is None:
                raise RuntimeError("INSERT certificates returned no row")
            return _row_from_db(fetched)
        except Exception as exc:
            if self._is_user_course_unique_violation(exc):
                existing = self.get_by_user_course(row.user_sub, row.course_id)
                if existing is not None:
                    return existing
            raise

    def get_by_credential_id(self, credential_id: str) -> Optional[CertificateRow]:
        cur = self._execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM certificates
            WHERE upper(credential_id) = upper(%s)
            """,
            (credential_id,),
        )
        row = cur.fetchone()
        return _row_from_db(row) if row else None

    def get_by_user_course(self, user_sub: str, course_id: str) -> Optional[CertificateRow]:
        cur = self._execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM certificates
            WHERE user_sub = %s AND course_id = %s
            """,
            (user_sub, course_id),
        )
        row = cur.fetchone()
        return _row_from_db(row) if row else None

    def list_for_user(self, user_sub: str) -> List[CertificateRow]:
        cur = self._execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM certificates
            WHERE user_sub = %s
            ORDER BY issue_date DESC, created_at DESC
            """,
            (user_sub,),
        )
        return [_row_from_db(r) for r in cur.fetchall()]

    def list_for_course(self, course_id: str) -> List[CertificateRow]:
        cur = self._execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM certificates
            WHERE course_id = %s
            ORDER BY issue_date DESC, created_at DESC
            """,
            (course_id,),
        )
        return [_row_from_db(r) for r in cur.fetchall()]

    def get_by_id(self, certificate_id: str) -> Optional[CertificateRow]:
        cur = self._execute(
            f"""
            SELECT {_SELECT_COLS}
            FROM certificates
            WHERE id = %s
            """,
            (certificate_id,),
        )
        row = cur.fetchone()
        return _row_from_db(row) if row else None

    def revoke(
        self,
        certificate_id: str,
        *,
        revoked_by: str,
        revoked_at: datetime,
    ) -> CertificateRow:
        cur = self._execute(
            f"""
            UPDATE certificates
               SET status = 'revoked',
                   revoked_at = %s,
                   revoked_by = %s
             WHERE id = %s
         RETURNING {_SELECT_COLS}
            """,
            (revoked_at, revoked_by, certificate_id),
            commit=True,
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"revoke target missing: {certificate_id}")
        return _row_from_db(row)
