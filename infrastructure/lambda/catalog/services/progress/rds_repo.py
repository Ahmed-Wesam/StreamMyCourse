"""PostgreSQL adapter for :class:`LessonProgressRepositoryPort`.

Implements lesson progress persistence using PostgreSQL with:
- Parameterized queries (no SQL injection)
- ON CONFLICT UPDATE for upserts
- Connection retry on OperationalError
- Returns LessonProgressRow dataclass instances
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional

from services.progress.ports import LessonProgressRepositoryPort, LessonProgressRow

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
