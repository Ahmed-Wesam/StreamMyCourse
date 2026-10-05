"""PostgreSQL adapter for :class:`LessonProgressRepositoryPort`.

Implements lesson progress persistence using PostgreSQL with:
- Parameterized queries (no SQL injection)
- ON CONFLICT UPDATE for upserts
- Connection retry on OperationalError
- Returns LessonProgressRow dataclass instances
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Callable, List, Optional

from services.progress.ports import ActivityEvent, LessonProgressRepositoryPort, LessonProgressRow

try:  # pragma: no cover - optional dependency path
    import psycopg2
    from psycopg2 import OperationalError
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]
    OperationalError = Exception  # type: ignore[misc, assignment]


logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]


class LessonProgressRdsRepository(LessonProgressRepositoryPort):
    """PostgreSQL repository for lesson progress data.

    Args:
        conn_factory: Callable that returns a psycopg2 connection
    """

    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

    def _connection(self) -> Any:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _execute(
        self, sql: str, params: tuple = (), *, commit: bool = False
    ) -> Any:
        """Execute SQL with automatic retry on connection failure.

        Args:
            sql: SQL query string
            params: Query parameters (tuple)
            commit: Whether to commit after execution

        Returns:
            Database cursor

        Raises:
            OperationalError: If connection fails after retry
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            return cur
        except Exception as exc:
            # Retry once on operational error (connection lost)
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
            conn.rollback()
            raise

    def get_progress_for_course(
        self, *, user_sub: str, course_id: str
    ) -> List[LessonProgressRow]:
        """Fetch all lesson progress records for a user in a specific course.

        Args:
            user_sub: User identifier (Cognito sub)
            course_id: Course identifier

        Returns:
            List of LessonProgressRow for all lessons in the course
        """
        cur = self._execute(
            """
            SELECT user_sub, lesson_id, course_id, completed, completed_at,
                   last_position_sec, updated_at
            FROM lesson_progress
            WHERE user_sub = %s AND course_id = %s
            ORDER BY lesson_id
            """,
            (user_sub, course_id),
        )

        rows: List[LessonProgressRow] = []
        for row in cur.fetchall():
            rows.append(
                LessonProgressRow(
                    user_sub=row[0],
                    lesson_id=row[1],
                    course_id=row[2],
                    completed=row[3],
                    completed_at=row[4],
                    last_position_sec=row[5],
                    updated_at=row[6],
                )
            )
        return rows

    def get_progress_for_lesson(
        self, *, user_sub: str, lesson_id: str
    ) -> Optional[LessonProgressRow]:
        """Fetch progress for a specific user and lesson.

        Args:
            user_sub: User identifier (Cognito sub)
            lesson_id: Lesson identifier

        Returns:
            LessonProgressRow if found, None otherwise
        """
        cur = self._execute(
            """
            SELECT user_sub, lesson_id, course_id, completed, completed_at,
                   last_position_sec, updated_at
            FROM lesson_progress
            WHERE user_sub = %s AND lesson_id = %s
            """,
            (user_sub, lesson_id),
        )

        row = cur.fetchone()
        if row is None:
            return None

        return LessonProgressRow(
            user_sub=row[0],
            lesson_id=row[1],
            course_id=row[2],
            completed=row[3],
            completed_at=row[4],
            last_position_sec=row[5],
            updated_at=row[6],
        )

    def upsert_progress(
        self,
        *,
        user_sub: str,
        lesson_id: str,
        course_id: str,
        completed: bool,
        last_position_sec: int,
    ) -> LessonProgressRow:
        """Create or update progress for a lesson.

        Uses atomic SQL CASE expressions to handle completed_at timing,
        eliminating TOCTOU race conditions. The database determines:
        - Set completed_at = NOW() only when transitioning to completed=True
        - Preserve existing completed_at if already completed
        - Clear completed_at if setting completed=False

        Args:
            user_sub: User identifier (Cognito sub)
            lesson_id: Lesson identifier
            course_id: Course identifier
            completed: Whether the lesson is completed
            last_position_sec: Last playback position in seconds

        Returns:
            LessonProgressRow with the resulting state
        """
        cur = self._execute(
            """
            INSERT INTO lesson_progress (
                user_sub, lesson_id, course_id, completed, completed_at,
                last_position_sec, updated_at
            ) VALUES (%s, %s, %s, %s,
                CASE WHEN %s THEN NOW() ELSE NULL END,
                %s, NOW())
            ON CONFLICT (user_sub, lesson_id) DO UPDATE SET
                completed = EXCLUDED.completed,
                completed_at = CASE
                    WHEN EXCLUDED.completed AND NOT lesson_progress.completed THEN NOW()
                    WHEN NOT EXCLUDED.completed THEN NULL
                    ELSE lesson_progress.completed_at
                END,
                last_position_sec = EXCLUDED.last_position_sec,
                updated_at = NOW()
            RETURNING user_sub, lesson_id, course_id, completed, completed_at,
                      last_position_sec, updated_at
            """,
            (user_sub, lesson_id, course_id, completed, completed, last_position_sec),
            commit=True,
        )

        row = cur.fetchone()
        return LessonProgressRow(
            user_sub=row[0],
            lesson_id=row[1],
            course_id=row[2],
            completed=row[3],
            completed_at=row[4],
            last_position_sec=row[5],
            updated_at=row[6],
        )

    def record_activity_day(self, *, user_sub: str, day: date) -> None:
        self._execute(
            """
            INSERT INTO learning_activity_days (user_sub, day)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (user_sub, day),
            commit=True,
        )

    def list_activity_days(self, *, user_sub: str) -> list[date]:
        cur = self._execute(
            "SELECT day FROM learning_activity_days WHERE user_sub = %s",
            (user_sub,),
        )
        return [_as_date(row[0]) for row in cur.fetchall()]

    def list_lesson_completions(self, *, user_sub: str) -> list[ActivityEvent]:
        cur = self._execute(
            """
            SELECT lp.user_sub, lp.completed_at, l.title, lp.course_id, lp.lesson_id
            FROM lesson_progress lp
            JOIN lessons l ON l.id = lp.lesson_id
            WHERE lp.user_sub = %s
              AND lp.completed = TRUE
              AND lp.completed_at IS NOT NULL
            """,
            (user_sub,),
        )
        return [_lesson_completion(row) for row in cur.fetchall()]

    def list_quiz_attempts(self, *, user_sub: str) -> list[ActivityEvent]:
        cur = self._execute(
            """
            SELECT b.user_sub, a.submitted_at, b.course_id, a.id
            FROM module_quiz_attempts a
            JOIN student_module_quiz_bindings b ON b.id = a.binding_id
            WHERE b.user_sub = %s
              AND a.status = 'submitted'
              AND a.submitted_at IS NOT NULL
            """,
            (user_sub,),
        )
        return [
            ActivityEvent(
                kind="quiz_attempt",
                occurred_at=_as_datetime(row[1]),
                title="Quiz",
                course_id=str(row[2]),
                resource_id=str(row[3]),
                user_sub=str(row[0]),
            )
            for row in cur.fetchall()
        ]

    def list_assignment_submissions(self, *, user_sub: str) -> list[ActivityEvent]:
        cur = self._execute(
            """
            SELECT s.user_sub, s.submitted_at, a.title, a.course_id, s.id
            FROM assignment_submissions s
            JOIN assignments a ON a.id = s.assignment_id
            WHERE s.user_sub = %s
              AND s.submitted_at IS NOT NULL
              AND s.status IN ('submitted', 'graded')
            """,
            (user_sub,),
        )
        return [
            ActivityEvent(
                kind="assignment_submission",
                occurred_at=_as_datetime(row[1]),
                title=str(row[2] or "Assignment"),
                course_id=str(row[3]),
                resource_id=str(row[4]),
                user_sub=str(row[0]),
            )
            for row in cur.fetchall()
        ]

    def list_certificates(self, *, user_sub: str) -> list[ActivityEvent]:
        cur = self._execute(
            """
            SELECT user_sub, created_at, course_title, course_id, credential_id
            FROM certificates
            WHERE user_sub = %s
              AND status = 'valid'
            """,
            (user_sub,),
        )
        return [
            ActivityEvent(
                kind="certificate",
                occurred_at=_as_datetime(row[1]),
                title=str(row[2] or "Certificate"),
                course_id=str(row[3]),
                resource_id=str(row[4]),
                user_sub=str(row[0]),
            )
            for row in cur.fetchall()
        ]


def _lesson_completion(row: tuple) -> ActivityEvent:
    return ActivityEvent(
        kind="lesson_completion",
        occurred_at=_as_datetime(row[1]),
        title=str(row[2] or "Lesson"),
        course_id=str(row[3]),
        resource_id=str(row[4]),
        user_sub=str(row[0]),
    )


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.date()
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _as_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed
