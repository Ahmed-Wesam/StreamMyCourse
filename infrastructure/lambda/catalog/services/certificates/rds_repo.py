"""PostgreSQL adapter for :class:`CertificatesRepositoryPort`."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, List, Optional
from uuid import uuid4

from services.certificates.ports import (
    BundleCertificateRow,
    CertificateRow,
    CertificatesRepositoryPort,
)
from services.common.db_tx import delete_in_batches, run_transaction

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

_BUNDLE_SELECT_COLS = """
    id, user_sub, credential_id, student_name, issue_date,
    instructor_name, instructor_title, status, revoked_at, revoked_by
"""

_DELETE_CERTIFICATES_FOR_COURSE_SQL = """
DELETE FROM certificates AS t
USING (
    SELECT id FROM certificates
    WHERE course_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""

_DELETE_CERTIFICATES_FOR_USER_SQL = """
DELETE FROM certificates AS t
USING (
    SELECT id FROM certificates
    WHERE user_sub = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""

_DELETE_BUNDLE_CERTIFICATES_FOR_USER_SQL = """
DELETE FROM bundle_certificates AS t
USING (
    SELECT id FROM bundle_certificates
    WHERE user_sub = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""


def _bundle_row_from_db(row: tuple) -> BundleCertificateRow:
    return BundleCertificateRow(
        id=str(row[0]),
        user_sub=str(row[1]),
        credential_id=str(row[2]),
        student_name=str(row[3]),
        issue_date=row[4],
        instructor_name=str(row[5]),
        instructor_title=str(row[6]),
        status=str(row[7]),
        revoked_at=row[8],
        revoked_by=str(row[9]) if row[9] is not None else None,
    )


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

    def _is_bundle_user_unique_violation(self, exc: BaseException) -> bool:
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
            "bundle_certificates_user_sub" in constraint
            or "bundle_certificates_user_sub_key" in constraint
            or "bundle_certificates_user_sub" in message
        )

    def insert_certificate(self, row: CertificateRow) -> CertificateRow:
        cert_id = row.id or str(uuid4())
        conn = self._connection()
        insert_sql = f"""
            INSERT INTO certificates (
                id, user_sub, course_id, credential_id, student_name, course_title,
                issue_date, instructor_name, instructor_title, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (user_sub, course_id) DO NOTHING
            RETURNING {_SELECT_COLS}
            """
        insert_params = (
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
        )

        def body() -> CertificateRow:
            cur = conn.cursor()
            cur.execute(insert_sql, insert_params)
            fetched = cur.fetchone()
            if fetched is not None:
                return _row_from_db(fetched)
            cur.execute(
                f"""
                SELECT {_SELECT_COLS}
                FROM certificates
                WHERE user_sub = %s AND course_id = %s
                """,
                (row.user_sub, row.course_id),
            )
            existing = cur.fetchone()
            if existing is None:
                raise RuntimeError("INSERT certificates conflicted but row missing")
            return _row_from_db(existing)

        try:
            return run_transaction(conn, body)
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
        conn = self._connection()
        sql = f"""
            UPDATE certificates
               SET status = 'revoked',
                   revoked_at = %s,
                   revoked_by = %s
             WHERE id = %s
         RETURNING {_SELECT_COLS}
            """
        params = (revoked_at, revoked_by, certificate_id)

        def body() -> CertificateRow:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"revoke target missing: {certificate_id}")
            return _row_from_db(row)

        return run_transaction(conn, body)

    def get_bundle_by_user(self, user_sub: str) -> Optional[BundleCertificateRow]:
        cur = self._execute(
            f"""
            SELECT {_BUNDLE_SELECT_COLS}
            FROM bundle_certificates
            WHERE user_sub = %s
            """,
            (user_sub,),
        )
        row = cur.fetchone()
        return _bundle_row_from_db(row) if row else None

    def insert_bundle_certificate(self, row: BundleCertificateRow) -> BundleCertificateRow:
        cert_id = row.id or str(uuid4())
        conn = self._connection()
        insert_sql = f"""
            INSERT INTO bundle_certificates (
                id, user_sub, credential_id, student_name, issue_date,
                instructor_name, instructor_title, status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (user_sub) DO NOTHING
            RETURNING {_BUNDLE_SELECT_COLS}
            """
        insert_params = (
            cert_id,
            row.user_sub,
            row.credential_id,
            row.student_name,
            row.issue_date,
            row.instructor_name,
            row.instructor_title,
            row.status,
        )

        def body() -> BundleCertificateRow:
            cur = conn.cursor()
            cur.execute(insert_sql, insert_params)
            fetched = cur.fetchone()
            if fetched is not None:
                return _bundle_row_from_db(fetched)
            cur.execute(
                f"""
                SELECT {_BUNDLE_SELECT_COLS}
                FROM bundle_certificates
                WHERE user_sub = %s
                """,
                (row.user_sub,),
            )
            existing = cur.fetchone()
            if existing is None:
                raise RuntimeError("INSERT bundle_certificates conflicted but row missing")
            return _bundle_row_from_db(existing)

        try:
            return run_transaction(conn, body)
        except Exception as exc:
            if self._is_bundle_user_unique_violation(exc):
                existing = self.get_bundle_by_user(row.user_sub)
                if existing is not None:
                    return existing
            raise

    def get_bundle_by_credential_id(
        self, credential_id: str
    ) -> Optional[BundleCertificateRow]:
        cur = self._execute(
            f"""
            SELECT {_BUNDLE_SELECT_COLS}
            FROM bundle_certificates
            WHERE upper(credential_id) = upper(%s)
            """,
            (credential_id,),
        )
        row = cur.fetchone()
        return _bundle_row_from_db(row) if row else None

    def revoke_bundle_for_user(
        self,
        user_sub: str,
        *,
        revoked_by: str,
        revoked_at: datetime,
    ) -> Optional[BundleCertificateRow]:
        conn = self._connection()
        sql = f"""
            UPDATE bundle_certificates
               SET status = 'revoked',
                   revoked_at = %s,
                   revoked_by = %s
             WHERE user_sub = %s
               AND status = 'valid'
         RETURNING {_BUNDLE_SELECT_COLS}
            """
        params = (revoked_at, revoked_by, user_sub)

        def body() -> Optional[BundleCertificateRow]:
            cur = conn.cursor()
            cur.execute(sql, params)
            row = cur.fetchone()
            return _bundle_row_from_db(row) if row else None

        return run_transaction(conn, body)

    def _batched_delete(self, sql: str, params: tuple) -> int:
        return delete_in_batches(self._connection(), sql, params)

    def delete_certificates_for_course(self, course_id: str) -> int:
        return self._batched_delete(_DELETE_CERTIFICATES_FOR_COURSE_SQL, (course_id,))

    def delete_certificates_for_user(self, user_sub: str) -> int:
        return self._batched_delete(_DELETE_CERTIFICATES_FOR_USER_SQL, (user_sub,))

    def delete_bundle_certificates_for_user(self, user_sub: str) -> int:
        return self._batched_delete(_DELETE_BUNDLE_CERTIFICATES_FOR_USER_SQL, (user_sub,))
