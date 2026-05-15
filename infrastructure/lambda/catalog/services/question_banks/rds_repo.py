"""PostgreSQL persistence for question banks and module quizzes (QB-A)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Callable, Optional

try:  # pragma: no cover - optional dependency path
    import psycopg2
    from psycopg2 import errors as pg_errors
    from psycopg2.extras import Json as PgJson
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]
    pg_errors = None  # type: ignore[assignment]
    PgJson = None  # type: ignore[assignment]

from services.common.errors import BadRequest, Conflict, NotFound
from services.question_banks.mcq_validation import validate_draft_question_for_publish
from services.question_banks.models import ModuleQuiz, Question, QuestionBank

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]


def _to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def _options_json_to_str(value: Any) -> str:
    if value is None:
        return "[]"
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _pg_json(value: Any) -> Any:
    if PgJson is not None:
        return PgJson(value)
    return json.dumps(value)


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

    @staticmethod
    def _raise_question_integrity(exc: BaseException) -> None:
        if pg_errors is None or psycopg2 is None:
            raise exc
        if isinstance(exc, pg_errors.ForeignKeyViolation):
            raise BadRequest(
                "course_id and question_bank_id must reference an existing course "
                "and question bank for that course"
            ) from exc
        if isinstance(exc, pg_errors.CheckViolation):
            raise BadRequest(
                "Invalid question data (e.g. status must be DRAFT or PUBLISHED)"
            ) from exc
        if isinstance(exc, psycopg2.IntegrityError):
            raise BadRequest("Database integrity constraint failed") from exc
        raise exc

    @staticmethod
    def _question_from_row(row: tuple[Any, ...]) -> Question:
        (
            qid,
            course_id,
            bank_id,
            status,
            prompt_text,
            options_json,
            correct_key,
            created_at,
            updated_at,
        ) = row
        return Question(
            id=str(qid),
            bankId=str(bank_id),
            courseId=str(course_id),
            status=str(status),
            promptText=str(prompt_text or ""),
            optionsJson=_options_json_to_str(options_json),
            correctOptionKey=str(correct_key) if correct_key is not None else None,
            createdAt=_to_iso(created_at),
            updatedAt=_to_iso(updated_at),
        )

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

    def get_bank_for_course(
        self, *, course_id: str, bank_id: str
    ) -> Optional[QuestionBank]:
        cur = self._execute(
            """
            SELECT id, course_id, status, created_at, updated_at
            FROM question_banks
            WHERE id = %s AND course_id = %s
            """,
            (bank_id, course_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        bid, cid, status, created_at, updated_at = row
        return QuestionBank(
            id=str(bid),
            courseId=str(cid),
            status=str(status),
            createdAt=_to_iso(created_at),
            updatedAt=_to_iso(updated_at),
        )

    def list_draft_questions(self, *, bank_id: str) -> list[Question]:
        cur = self._execute(
            """
            SELECT id, course_id, question_bank_id, status, prompt_text, options_json,
                   correct_option_key, created_at, updated_at
            FROM questions
            WHERE question_bank_id = %s AND status = 'DRAFT'
            ORDER BY created_at ASC, id ASC
            """,
            (bank_id,),
        )
        return [self._question_from_row(row) for row in cur.fetchall()]

    def publish_bank_transaction(
        self,
        *,
        course_id: str,
        bank_id: str,
        module_id: str,
        n: int,
    ) -> None:
        conn = self._connection()
        prev_autocommit = getattr(conn, "autocommit", False)
        conn.autocommit = False
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id, status
                FROM question_banks
                WHERE id = %s AND course_id = %s
                FOR UPDATE
                """,
                (bank_id, course_id),
            )
            bank_row = cur.fetchone()
            if bank_row is None:
                raise NotFound("Question bank not found for this course")
            bank_status = str(bank_row[1])
            if bank_status != "DRAFT":
                raise Conflict("Question bank is not in DRAFT status")

            cur.execute(
                """
                SELECT COUNT(*)::int
                FROM questions
                WHERE course_id = %s AND question_bank_id = %s AND status = 'DRAFT'
                """,
                (course_id, bank_id),
            )
            draft_total = int(cur.fetchone()[0])
            if draft_total == 0:
                raise BadRequest("Cannot publish: question bank has no draft questions")
            if n > draft_total:
                raise BadRequest(
                    "Cannot publish: N is greater than the number of draft questions"
                )

            cur.execute(
                """
                SELECT COUNT(*)::int
                FROM questions
                WHERE course_id = %s AND question_bank_id = %s AND status = 'DRAFT'
                  AND (
                      correct_option_key IS NULL
                      OR btrim(correct_option_key::text) = ''
                  )
                """,
                (course_id, bank_id),
            )
            missing_correct = int(cur.fetchone()[0])
            if missing_correct > 0:
                raise BadRequest(
                    "Cannot publish: every draft question must have a designated "
                    "correct answer"
                )

            cur.execute(
                """
                SELECT correct_option_key, options_json
                FROM questions
                WHERE course_id = %s AND question_bank_id = %s AND status = 'DRAFT'
                """,
                (course_id, bank_id),
            )
            for correct_key, options_json in cur.fetchall():
                validate_draft_question_for_publish(
                    correct_option_key=(
                        str(correct_key) if correct_key is not None else None
                    ),
                    options_json=options_json,
                )

            cur.execute(
                """
                UPDATE questions
                SET status = 'PUBLISHED', updated_at = NOW()
                WHERE course_id = %s AND question_bank_id = %s AND status = 'DRAFT'
                """,
                (course_id, bank_id),
            )
            published_rows = cur.rowcount
            if published_rows != draft_total:
                raise BadRequest("Cannot publish: draft question set changed during publish")

            cur.execute(
                """
                UPDATE question_banks
                SET status = 'PUBLISHED', updated_at = NOW()
                WHERE course_id = %s AND id = %s AND status = 'DRAFT'
                """,
                (course_id, bank_id),
            )
            if cur.rowcount != 1:
                raise Conflict("Question bank is not in DRAFT status")

            cur.execute(
                """
                UPDATE module_quizzes
                SET served_count_n = %s, updated_at = NOW()
                WHERE course_id = %s AND module_id = %s AND question_bank_id = %s
                """,
                (n, course_id, module_id, bank_id),
            )
            if cur.rowcount != 1:
                raise BadRequest(
                    "No module quiz row for this module linked to this question bank"
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit = prev_autocommit

    def get_question_by_id(
        self, *, bank_id: str, question_id: str
    ) -> Optional[Question]:
        cur = self._execute(
            """
            SELECT id, course_id, question_bank_id, status, prompt_text, options_json,
                   correct_option_key, created_at, updated_at
            FROM questions
            WHERE id = %s AND question_bank_id = %s
            """,
            (question_id, bank_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._question_from_row(row)

    def insert_draft_question(
        self,
        *,
        course_id: str,
        bank_id: str,
        prompt_text: str,
        options_json: Any,
        correct_option_key: Optional[str] = None,
    ) -> str:
        try:
            cur = self._execute(
                """
                INSERT INTO questions (
                    course_id, question_bank_id, status,
                    prompt_text, options_json, correct_option_key
                )
                VALUES (%s, %s, 'DRAFT', %s, %s, %s)
                RETURNING id
                """,
                (
                    course_id,
                    bank_id,
                    prompt_text,
                    _pg_json(options_json),
                    (correct_option_key or "").strip() or None,
                ),
                commit=True,
            )
        except Exception as exc:
            self._raise_question_integrity(exc)
        row = cur.fetchone()
        if not row:
            raise RuntimeError("INSERT questions returned no row")
        return str(row[0])

    def insert_published_question(
        self, *, course_id: str, bank_id: str, correct_option_key: str
    ) -> str:
        key = (correct_option_key or "").strip()
        if not key:
            raise BadRequest("correct_option_key is required")
        options: list[dict[str, str]] = [{"key": key, "text": ""}]
        try:
            cur = self._execute(
                """
                INSERT INTO questions (
                    course_id, question_bank_id, status,
                    prompt_text, options_json, correct_option_key
                )
                VALUES (%s, %s, 'PUBLISHED', %s, %s, %s)
                RETURNING id
                """,
                (course_id, bank_id, "", _pg_json(options), key),
                commit=True,
            )
        except Exception as exc:
            self._raise_question_integrity(exc)
        row = cur.fetchone()
        if not row:
            raise RuntimeError("INSERT questions returned no row")
        return str(row[0])

    def update_question(
        self,
        *,
        course_id: str,
        bank_id: str,
        question_id: str,
        prompt_text: Optional[str] = None,
        options_json: Any = None,
        correct_option_key: Optional[str] = None,
    ) -> None:
        set_parts = ["updated_at = NOW()"]
        args: list[Any] = []
        if prompt_text is not None:
            set_parts.append("prompt_text = %s")
            args.append(prompt_text)
        if options_json is not None:
            set_parts.append("options_json = %s")
            args.append(_pg_json(options_json))
        if correct_option_key is not None:
            set_parts.append("correct_option_key = %s")
            args.append(
                (correct_option_key or "").strip() or None,
            )
        args.extend([question_id, course_id, bank_id])
        sql = f"""
            UPDATE questions
            SET {", ".join(set_parts)}
            WHERE id = %s AND course_id = %s AND question_bank_id = %s
              AND status = 'DRAFT'
        """
        try:
            cur = self._execute(sql, tuple(args), commit=True)
        except Exception as exc:
            self._raise_question_integrity(exc)
        if cur.rowcount != 1:
            raise NotFound("Question not found for this bank")

    def delete_question(
        self, *, course_id: str, bank_id: str, question_id: str
    ) -> None:
        try:
            cur = self._execute(
                """
                DELETE FROM questions
                WHERE id = %s AND course_id = %s AND question_bank_id = %s
                  AND status = 'DRAFT'
                """,
                (question_id, course_id, bank_id),
                commit=True,
            )
        except Exception as exc:
            self._raise_question_integrity(exc)
        if cur.rowcount != 1:
            raise NotFound("Question not found for this bank")

    def list_module_quiz_visibility_for_course(
        self, *, course_id: str
    ) -> dict[str, dict[str, int]]:
        """Modules with a published bank and served N >= 1 for this course."""
        cur = self._execute(
            """
            SELECT mq.module_id, mq.served_count_n
            FROM module_quizzes mq
            INNER JOIN question_banks qb
              ON qb.id = mq.question_bank_id AND qb.course_id = %s
            WHERE mq.course_id = %s
              AND mq.question_bank_id IS NOT NULL
              AND qb.status = 'PUBLISHED'
              AND mq.served_count_n IS NOT NULL
              AND mq.served_count_n >= 1
            """,
            (course_id, course_id),
        )
        result: dict[str, dict[str, int]] = {}
        for module_id, served_n in cur.fetchall():
            result[str(module_id)] = {"servedCountN": int(served_n)}
        return result

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
