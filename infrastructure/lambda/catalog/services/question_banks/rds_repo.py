"""PostgreSQL persistence for question banks and module quizzes (QB-A)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
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
from services.question_banks.models import (
    BoundQuestion,
    ModuleQuiz,
    ModuleQuizAttempt,
    ModuleQuizAttemptBindingContext,
    ModuleQuizSubmissionSnapshot,
    PublishedQuestionGradingRow,
    Question,
    QuestionBank,
    StudentModuleQuizBinding,
)

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
    def _raise_binding_integrity(exc: BaseException) -> None:
        if pg_errors is None or psycopg2 is None:
            raise exc
        if isinstance(exc, pg_errors.UniqueViolation):
            raise Conflict(
                "Student module quiz binding already exists for this quiz"
            ) from exc
        if isinstance(exc, pg_errors.ForeignKeyViolation):
            raise BadRequest(
                "module_quiz_id, course_id, and question_id must reference "
                "valid module_quizzes and questions rows for the same course"
            ) from exc
        if isinstance(exc, psycopg2.IntegrityError):
            raise BadRequest("Database integrity constraint failed") from exc
        raise exc

    @staticmethod
    def _attempt_unique_violation_message(exc: Any) -> str:
        constraint = ""
        diag = getattr(exc, "diag", None)
        if diag is not None:
            name = getattr(diag, "constraint_name", None)
            if name:
                constraint = str(name)
        if constraint == "uq_module_quiz_attempts_one_in_progress":
            return "Module quiz attempt already in progress for this binding"
        if constraint == "module_quiz_attempts_binding_id_attempt_number_key":
            return (
                "Module quiz attempt number already exists for this binding"
            )
        return "Module quiz attempt already exists for this binding"

    @classmethod
    def _raise_attempt_integrity(cls, exc: BaseException) -> None:
        if pg_errors is None or psycopg2 is None:
            raise exc
        if isinstance(exc, pg_errors.UniqueViolation):
            raise Conflict(cls._attempt_unique_violation_message(exc)) from exc
        if isinstance(exc, pg_errors.ForeignKeyViolation):
            raise BadRequest(
                "binding_id must reference a valid student_module_quiz_bindings row"
            ) from exc
        if isinstance(exc, pg_errors.CheckViolation):
            raise BadRequest(
                "Invalid module quiz attempt data "
                "(attempt_number, status, or shuffle JSON shape)"
            ) from exc
        if isinstance(exc, psycopg2.IntegrityError):
            raise BadRequest("Database integrity constraint failed") from exc
        raise exc

    @classmethod
    def _raise_submission_integrity(cls, exc: BaseException) -> None:
        if pg_errors is None or psycopg2 is None:
            raise exc
        if isinstance(exc, pg_errors.UniqueViolation):
            raise Conflict(
                "Submission already recorded for this module quiz attempt"
            ) from exc
        if isinstance(exc, pg_errors.ForeignKeyViolation):
            raise BadRequest(
                "attempt_id must reference an existing module_quiz_attempts row"
            ) from exc
        if isinstance(exc, pg_errors.CheckViolation):
            raise BadRequest(
                "Invalid module quiz submission data (answers JSON or score bounds)"
            ) from exc
        if isinstance(exc, psycopg2.IntegrityError):
            raise BadRequest("Database integrity constraint failed") from exc
        raise exc

    @staticmethod
    def _jsonb_to_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        return []

    @staticmethod
    def _jsonb_to_choice_orders(value: Any) -> dict[str, list[str]]:
        if value is None:
            return {}
        raw: Any = value
        if isinstance(value, str):
            raw = json.loads(value)
        if not isinstance(raw, dict):
            return {}
        out: dict[str, list[str]] = {}
        for key, order in raw.items():
            if isinstance(order, list):
                out[str(key)] = [str(v) for v in order]
        return out

    @staticmethod
    def _jsonb_to_answers_map(value: Any) -> dict[str, str]:
        if value is None:
            return {}
        raw: Any = value
        if isinstance(value, str):
            raw = json.loads(value)
        if not isinstance(raw, dict):
            return {}
        return {str(k): str(v) for k, v in raw.items()}

    @classmethod
    def _row_to_attempt(cls, row: tuple[Any, ...]) -> ModuleQuizAttempt:
        (
            attempt_id,
            binding_id,
            attempt_number,
            status,
            question_order,
            choice_orders,
            started_at,
            submitted_at,
        ) = row
        return ModuleQuizAttempt(
            id=str(attempt_id),
            bindingId=str(binding_id),
            attemptNumber=int(attempt_number),
            status=str(status),
            shuffledQuestionOrder=cls._jsonb_to_list(question_order),
            shuffledChoiceOrders=cls._jsonb_to_choice_orders(choice_orders),
            startedAt=_to_iso(started_at),
            submittedAt=_to_iso(submitted_at) if submitted_at is not None else None,
        )

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

    def list_published_question_ids(
        self, *, course_id: str, bank_id: str
    ) -> list[str]:
        cur = self._execute(
            """
            SELECT id
            FROM questions
            WHERE course_id = %s AND question_bank_id = %s AND status = 'PUBLISHED'
            ORDER BY created_at ASC, id ASC
            """,
            (course_id, bank_id),
        )
        return [str(row[0]) for row in cur.fetchall()]

    def list_student_bound_questions(
        self, *, course_id: str, question_ids: list[str]
    ) -> list[BoundQuestion]:
        if not question_ids:
            return []
        cur = self._execute(
            """
            SELECT id, prompt_text, options_json
            FROM questions
            WHERE course_id = %s AND id = ANY(%s::uuid[])
            """,
            (course_id, question_ids),
        )
        by_id: dict[str, BoundQuestion] = {}
        for qid, prompt_text, options_json in cur.fetchall():
            by_id[str(qid)] = BoundQuestion(
                id=str(qid),
                promptText=str(prompt_text or ""),
                optionsJson=_options_json_to_str(options_json),
            )
        return [by_id[qid] for qid in question_ids if qid in by_id]

    def list_grading_rows_for_questions(
        self, *, course_id: str, question_ids: list[str]
    ) -> list[PublishedQuestionGradingRow]:
        """Load published MCQ rows for grading (includes ``correct_option_key``)."""
        if not question_ids:
            return []
        cur = self._execute(
            """
            SELECT id, prompt_text, options_json, correct_option_key
            FROM questions
            WHERE course_id = %s AND status = 'PUBLISHED' AND id = ANY(%s::uuid[])
            """,
            (course_id, question_ids),
        )
        by_id: dict[str, PublishedQuestionGradingRow] = {}
        for qid, prompt_text, options_json, correct_key in cur.fetchall():
            if correct_key is None:
                continue
            by_id[str(qid)] = PublishedQuestionGradingRow(
                id=str(qid),
                promptText=str(prompt_text or ""),
                optionsJson=_options_json_to_str(options_json),
                correctOptionKey=str(correct_key),
            )
        return [by_id[qid] for qid in question_ids if qid in by_id]

    def get_binding_for_student(
        self, *, module_quiz_id: str, user_sub: str
    ) -> Optional[StudentModuleQuizBinding]:
        cur = self._execute(
            """
            SELECT id, module_quiz_id, course_id, user_sub
            FROM student_module_quiz_bindings
            WHERE module_quiz_id = %s AND user_sub = %s
            """,
            (module_quiz_id, user_sub),
        )
        row = cur.fetchone()
        if not row:
            return None
        binding_id, mq_id, course_id, sub = row
        cur = self._execute(
            """
            SELECT question_id
            FROM student_module_quiz_binding_questions
            WHERE binding_id = %s
            ORDER BY position ASC
            """,
            (str(binding_id),),
        )
        question_ids = [str(r[0]) for r in cur.fetchall()]
        return StudentModuleQuizBinding(
            id=str(binding_id),
            moduleQuizId=str(mq_id),
            courseId=str(course_id),
            userSub=str(sub),
            questionIds=question_ids,
        )

    def insert_binding_with_questions(
        self,
        *,
        module_quiz_id: str,
        course_id: str,
        user_sub: str,
        question_ids: list[str],
    ) -> str:
        conn = self._connection()
        prev_autocommit = getattr(conn, "autocommit", False)
        conn.autocommit = False
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO student_module_quiz_bindings (
                    module_quiz_id, course_id, user_sub
                )
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (module_quiz_id, course_id, user_sub),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(
                    "INSERT student_module_quiz_bindings returned no row"
                )
            binding_id = str(row[0])
            for position, question_id in enumerate(question_ids):
                cur.execute(
                    """
                    INSERT INTO student_module_quiz_binding_questions (
                        binding_id, position, question_id
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (binding_id, position, question_id),
                )
            conn.commit()
            return binding_id
        except Exception as exc:
            conn.rollback()
            self._raise_binding_integrity(exc)
        finally:
            conn.autocommit = prev_autocommit

    def insert_binding_with_questions_and_initial_attempt(
        self,
        *,
        module_quiz_id: str,
        course_id: str,
        user_sub: str,
        question_ids: list[str],
        shuffled_question_order: list[str],
        shuffled_choice_orders: dict[str, list[str]],
    ) -> str:
        """Insert binding, binding questions, and attempt 1 in one transaction."""
        conn = self._connection()
        prev_autocommit = getattr(conn, "autocommit", False)
        conn.autocommit = False
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO student_module_quiz_bindings (
                    module_quiz_id, course_id, user_sub
                )
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (module_quiz_id, course_id, user_sub),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError(
                    "INSERT student_module_quiz_bindings returned no row"
                )
            binding_id = str(row[0])
            for position, question_id in enumerate(question_ids):
                cur.execute(
                    """
                    INSERT INTO student_module_quiz_binding_questions (
                        binding_id, position, question_id
                    )
                    VALUES (%s, %s, %s)
                    """,
                    (binding_id, position, question_id),
                )
            cur.execute(
                """
                INSERT INTO module_quiz_attempts (
                    binding_id,
                    attempt_number,
                    status,
                    shuffled_question_order,
                    shuffled_choice_orders
                )
                VALUES (%s, 1, 'in_progress', %s, %s)
                RETURNING id
                """,
                (
                    binding_id,
                    _pg_json(shuffled_question_order),
                    _pg_json(shuffled_choice_orders),
                ),
            )
            if not cur.fetchone():
                raise RuntimeError("INSERT module_quiz_attempts returned no row")
            conn.commit()
            return binding_id
        except Exception as exc:
            conn.rollback()
            if isinstance(exc, pg_errors.UniqueViolation):
                constraint = ""
                diag = getattr(exc, "diag", None)
                if diag is not None:
                    name = getattr(diag, "constraint_name", None)
                    if name:
                        constraint = str(name)
                if "student_module_quiz_bindings" in constraint:
                    self._raise_binding_integrity(exc)
                self._raise_attempt_integrity(exc)
            self._raise_binding_integrity(exc)
        finally:
            conn.autocommit = prev_autocommit

    _ATTEMPT_SELECT = """
            SELECT id, binding_id, attempt_number, status,
                   shuffled_question_order, shuffled_choice_orders,
                   started_at, submitted_at
            FROM module_quiz_attempts
    """

    def get_open_attempt(self, *, binding_id: str) -> Optional[ModuleQuizAttempt]:
        cur = self._execute(
            self._ATTEMPT_SELECT
            + """
            WHERE binding_id = %s AND status = 'in_progress'
            """,
            (binding_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_attempt(row)

    def get_latest_attempt(self, *, binding_id: str) -> Optional[ModuleQuizAttempt]:
        cur = self._execute(
            self._ATTEMPT_SELECT
            + """
            WHERE binding_id = %s
            ORDER BY attempt_number DESC
            LIMIT 1
            """,
            (binding_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_attempt(row)

    def insert_attempt_with_shuffle(
        self,
        *,
        binding_id: str,
        attempt_number: int,
        shuffled_question_order: list[str],
        shuffled_choice_orders: dict[str, list[str]],
    ) -> ModuleQuizAttempt:
        conn = self._connection()
        prev_autocommit = getattr(conn, "autocommit", False)
        conn.autocommit = False
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO module_quiz_attempts (
                    binding_id,
                    attempt_number,
                    status,
                    shuffled_question_order,
                    shuffled_choice_orders
                )
                VALUES (%s, %s, 'in_progress', %s, %s)
                RETURNING id, binding_id, attempt_number, status,
                          shuffled_question_order, shuffled_choice_orders,
                          started_at, submitted_at
                """,
                (
                    binding_id,
                    attempt_number,
                    _pg_json(shuffled_question_order),
                    _pg_json(shuffled_choice_orders),
                ),
            )
            row = cur.fetchone()
            if not row:
                raise RuntimeError("INSERT module_quiz_attempts returned no row")
            conn.commit()
            return self._row_to_attempt(row)
        except Exception as exc:
            conn.rollback()
            self._raise_attempt_integrity(exc)
        finally:
            conn.autocommit = prev_autocommit

    def mark_attempt_submitted(
        self,
        *,
        attempt_id: str,
        submitted_at: Optional[datetime] = None,
    ) -> None:
        when = submitted_at if submitted_at is not None else datetime.now(timezone.utc)
        cur = self._execute(
            """
            UPDATE module_quiz_attempts
            SET status = 'submitted', submitted_at = %s
            WHERE id = %s
            """,
            (when, attempt_id),
            commit=True,
        )
        if cur.rowcount < 1:
            raise NotFound("Module quiz attempt not found")

    def insert_submission_and_mark_submitted(
        self,
        *,
        attempt_id: str,
        answers_json: dict[str, str],
        correct_count: int,
        total_count: int,
        submitted_at: Optional[datetime] = None,
    ) -> None:
        """Insert ``module_quiz_attempt_submissions`` and mark the attempt submitted (one transaction)."""
        when = submitted_at if submitted_at is not None else datetime.now(timezone.utc)
        conn = self._connection()
        prev_autocommit = getattr(conn, "autocommit", False)
        conn.autocommit = False
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO module_quiz_attempt_submissions (
                    attempt_id, answers_json, correct_count, total_count, submitted_at
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    attempt_id,
                    _pg_json(answers_json),
                    correct_count,
                    total_count,
                    when,
                ),
            )
            cur.execute(
                """
                UPDATE module_quiz_attempts
                SET status = 'submitted', submitted_at = %s
                WHERE id = %s
                """,
                (when, attempt_id),
            )
            if cur.rowcount < 1:
                conn.rollback()
                raise NotFound("Module quiz attempt not found")
            conn.commit()
        except NotFound:
            raise
        except Exception as exc:
            conn.rollback()
            self._raise_submission_integrity(exc)
        finally:
            conn.autocommit = prev_autocommit

    def get_latest_submission_for_binding(
        self, *, binding_id: str
    ) -> Optional[ModuleQuizSubmissionSnapshot]:
        cur = self._execute(
            """
            SELECT s.attempt_id, a.attempt_number, s.answers_json, s.correct_count,
                   s.total_count, s.submitted_at
            FROM module_quiz_attempt_submissions s
            INNER JOIN module_quiz_attempts a ON a.id = s.attempt_id
            WHERE a.binding_id = %s
            ORDER BY s.submitted_at DESC, s.attempt_id DESC
            LIMIT 1
            """,
            (binding_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            att_id,
            attempt_number,
            answers_raw,
            correct_count,
            total_count,
            submitted_at,
        ) = row
        return ModuleQuizSubmissionSnapshot(
            attemptId=str(att_id),
            attemptNumber=int(attempt_number),
            answersJson=self._jsonb_to_answers_map(answers_raw),
            correctCount=int(correct_count),
            totalCount=int(total_count),
            submittedAt=_to_iso(submitted_at),
        )

    def get_attempt_with_binding_rows(
        self, *, attempt_id: str
    ) -> Optional[ModuleQuizAttemptBindingContext]:
        cur = self._execute(
            """
            SELECT a.id, a.binding_id, a.attempt_number, a.status,
                   a.shuffled_question_order, a.shuffled_choice_orders,
                   a.started_at, a.submitted_at,
                   b.module_quiz_id, b.course_id, b.user_sub,
                   mq.module_id
            FROM module_quiz_attempts a
            INNER JOIN student_module_quiz_bindings b ON b.id = a.binding_id
            INNER JOIN module_quizzes mq ON mq.id = b.module_quiz_id
            WHERE a.id = %s
            """,
            (attempt_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        (
            aid,
            binding_id,
            attempt_number,
            status,
            question_order,
            choice_orders,
            started_at,
            submitted_at,
            module_quiz_id,
            course_id,
            user_sub,
            module_id,
        ) = row
        attempt = ModuleQuizAttempt(
            id=str(aid),
            bindingId=str(binding_id),
            attemptNumber=int(attempt_number),
            status=str(status),
            shuffledQuestionOrder=self._jsonb_to_list(question_order),
            shuffledChoiceOrders=self._jsonb_to_choice_orders(choice_orders),
            startedAt=_to_iso(started_at),
            submittedAt=_to_iso(submitted_at) if submitted_at is not None else None,
        )
        return ModuleQuizAttemptBindingContext(
            attempt=attempt,
            moduleQuizId=str(module_quiz_id),
            courseId=str(course_id),
            moduleId=str(module_id),
            userSub=str(user_sub),
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
