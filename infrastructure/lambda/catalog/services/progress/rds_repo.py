"""PostgreSQL adapter for lesson progress."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional

try:  # pragma: no cover
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

from services.progress.ports import LessonProgressRow

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]


class LessonProgressRdsRepository:
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
                logger.warning("RDS connection lost, reconnecting and retrying once: %s", exc)
                self._conn = None
                conn = self._connection()
                cur = conn.cursor()
                cur.execute(sql, params)
                if commit:
                    conn.commit()
                return cur
            raise

    def list_for_course(self, *, user_sub: str, course_id: str) -> List[LessonProgressRow]:
        cur = self._execute(
            """
            SELECT lesson_id, course_id, user_sub, completed, completed_at, last_position_sec
            FROM lesson_progress
            WHERE user_sub = %s AND course_id = %s
            """,
            (user_sub, course_id),
        )
        rows: List[LessonProgressRow] = []
        for lesson_id, cid, usub, completed, completed_at, pos in cur.fetchall() or []:
            at_iso: Optional[str] = None
            if completed_at is not None:
                if isinstance(completed_at, datetime):
                    if completed_at.tzinfo is None:
                        completed_at = completed_at.replace(tzinfo=timezone.utc)
                    at_iso = completed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
                else:
                    at_iso = str(completed_at)
            rows.append(
                LessonProgressRow(
                    lesson_id=str(lesson_id),
                    course_id=str(cid),
                    user_sub=str(usub),
                    completed=bool(completed),
                    completed_at_iso=at_iso,
                    last_position_sec=int(pos or 0),
                )
            )
        return rows

    def upsert(
        self,
        *,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        last_position_sec: int,
        completed: bool,
        completed_at_iso: Optional[str],
    ) -> None:
        self._execute(
            """
            INSERT INTO lesson_progress (
                user_sub, lesson_id, course_id, last_position_sec, completed, completed_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (user_sub, lesson_id) DO UPDATE SET
                course_id = EXCLUDED.course_id,
                last_position_sec = EXCLUDED.last_position_sec,
                completed = EXCLUDED.completed,
                completed_at = EXCLUDED.completed_at,
                updated_at = NOW()
            """,
            (
                user_sub,
                lesson_id,
                course_id,
                last_position_sec,
                completed,
                completed_at_iso,
            ),
            commit=True,
        )
