"""PostgreSQL persistence for question banks and module quizzes (QB-A)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Optional

try:  # pragma: no cover - optional dependency path
    import psycopg2
    from psycopg2 import errors as pg_errors
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]
    pg_errors = None  # type: ignore[assignment]

from services.common.errors import BadRequest, Conflict
from services.question_banks.models import ModuleQuiz, QuestionBank

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


class QuestionBankRdsRepository:
    """Inserts and lookups for ``question_banks`` / ``module_quizzes`` tables."""

    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _execute(
        self, sql: str, params: tuple = (), *, commit: bool = False
    ) -> Any:
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            return cur
        except Exception as exc:
            if psycopg2 is not None and isinstance(exc, psycopg2.OperationalError):
                logger.warning(
                    "RDS connection lost, reconnecting and retrying once: %s", exc
                )
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

    @staticmethod
    def _raise_integrity(exc: BaseException, *, for_module_quiz: bool) -> None:
        if pg_errors is None or psycopg2 is None:
            raise exc
        if isinstance(exc, pg_errors.UniqueViolation):
            if for_module_quiz:
                raise Conflict("Module already has a quiz") from exc
            raise Conflict("Question bank insert conflict") from exc
        if isinstance(exc, pg_errors.ForeignKeyViolation):
            if for_module_quiz:
                raise BadRequest(
                    "course_id, module_id, and question_bank_id must reference "
                    "valid course_modules and question_banks rows for the same course"
                ) from exc
            raise BadRequest("course_id must reference an existing course") from exc
        if isinstance(exc, pg_errors.CheckViolation):
            if for_module_quiz:
                raise BadRequest(
                    "Invalid module quiz data (e.g. served_count_n must be null or at least 1)"
                ) from exc
            raise BadRequest(
                "Invalid question bank status (allowed values: DRAFT, PUBLISHED)"
            ) from exc
        if isinstance(exc, psycopg2.IntegrityError):
            raise BadRequest("Database integrity constraint failed") from exc
        raise exc

    def insert_question_bank(
        self, *, course_id: str, status: str = "DRAFT"
    ) -> str:
        """Create a course-scoped bank; returns new bank id."""
        try:
            cur = self._execute(
                """
                INSERT INTO question_banks (course_id, status)
                VALUES (%s, %s)
                RETURNING id
                """,
                (course_id, status),
                commit=True,
            )
        except Exception as exc:
            self._raise_integrity(exc, for_module_quiz=False)
        row = cur.fetchone()
        if not row:
            raise RuntimeError("INSERT question_banks returned no row")
        return str(row[0])

    def insert_module_quiz(
        self,
        *,
        course_id: str,
        module_id: str,
        question_bank_id: Optional[str] = None,
        served_count_n: Optional[int] = None,
    ) -> str:
        """Create at most one quiz row per module (enforced by UNIQUE(module_id))."""
        try:
            cur = self._execute(
                """
                INSERT INTO module_quizzes (
                    course_id, module_id, question_bank_id, served_count_n
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (course_id, module_id, question_bank_id, served_count_n),
                commit=True,
            )
        except Exception as exc:
            self._raise_integrity(exc, for_module_quiz=True)
        row = cur.fetchone()
        if not row:
            raise RuntimeError("INSERT module_quizzes returned no row")
        return str(row[0])

    def get_question_bank_by_id(self, *, bank_id: str) -> Optional[QuestionBank]:
        cur = self._execute(
            """
            SELECT id, course_id, status, created_at, updated_at
            FROM question_banks
            WHERE id = %s
            """,
            (bank_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        bid, course_id, status, created_at, updated_at = row
        return QuestionBank(
            id=str(bid),
            courseId=str(course_id),
            status=str(status),
            createdAt=_to_iso(created_at),
            updatedAt=_to_iso(updated_at),
        )

    def get_module_quiz_by_module_id(self, *, module_id: str) -> Optional[ModuleQuiz]:
        cur = self._execute(
            """
            SELECT id, course_id, module_id, question_bank_id, served_count_n,
                   created_at, updated_at
            FROM module_quizzes
            WHERE module_id = %s
            """,
            (module_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            qid,
            course_id,
            mid,
            bank_id,
            served_n,
            created_at,
            updated_at,
        ) = row
        return ModuleQuiz(
            id=str(qid),
            courseId=str(course_id),
            moduleId=str(mid),
            questionBankId=str(bank_id) if bank_id is not None else None,
            servedCountN=int(served_n) if served_n is not None else None,
            createdAt=_to_iso(created_at),
            updatedAt=_to_iso(updated_at),
        )
