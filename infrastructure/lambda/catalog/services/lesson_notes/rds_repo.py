"""PostgreSQL adapter for :class:`LessonNotesRepositoryPort`."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, List, Optional

from services.lesson_notes.ports import LessonNoteRow, LessonNotesRepositoryPort

try:  # pragma: no cover
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]


def _row_from_db(row: tuple) -> LessonNoteRow:
    return LessonNoteRow(
        id=str(row[0]),
        user_sub=row[1],
        course_id=str(row[2]),
        lesson_id=str(row[3]),
        body=row[4],
        timestamp_sec=row[5],
        created_at=row[6],
        updated_at=row[7],
    )


class LessonNotesRdsRepository(LessonNotesRepositoryPort):
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

    def list_notes_for_lesson(
        self, *, user_sub: str, course_id: str, lesson_id: str
    ) -> List[LessonNoteRow]:
        cur = self._execute(
            """
            SELECT id, user_sub, course_id, lesson_id, body, timestamp_sec,
                   created_at, updated_at
            FROM lesson_notes
            WHERE user_sub = %s AND course_id = %s AND lesson_id = %s
            ORDER BY created_at ASC, id ASC
            """,
            (user_sub, course_id, lesson_id),
        )
        return [_row_from_db(r) for r in cur.fetchall()]

    def count_notes_for_user_lesson(self, *, user_sub: str, lesson_id: str) -> int:
        cur = self._execute(
            """
            SELECT COUNT(*) FROM lesson_notes
            WHERE user_sub = %s AND lesson_id = %s
            """,
            (user_sub, lesson_id),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def get_note_for_user(self, *, note_id: str, user_sub: str) -> Optional[LessonNoteRow]:
        cur = self._execute(
            """
            SELECT id, user_sub, course_id, lesson_id, body, timestamp_sec,
                   created_at, updated_at
            FROM lesson_notes
            WHERE id = %s AND user_sub = %s
            """,
            (note_id, user_sub),
        )
        row = cur.fetchone()
        return _row_from_db(row) if row else None

    def insert_note(
        self,
        *,
        user_sub: str,
        course_id: str,
        lesson_id: str,
        body: str,
        timestamp_sec: Optional[int],
    ) -> LessonNoteRow:
        cur = self._execute(
            """
            INSERT INTO lesson_notes (
                user_sub, course_id, lesson_id, body, timestamp_sec, updated_at
            ) VALUES (%s, %s, %s, %s, %s, NOW())
            RETURNING id, user_sub, course_id, lesson_id, body, timestamp_sec,
                      created_at, updated_at
            """,
            (user_sub, course_id, lesson_id, body, timestamp_sec),
            commit=True,
        )
        row = cur.fetchone()
        return _row_from_db(row)

    def update_note(
        self,
        *,
        note_id: str,
        user_sub: str,
        body: str,
        timestamp_sec: Optional[int],
    ) -> LessonNoteRow:
        cur = self._execute(
            """
            UPDATE lesson_notes
            SET body = %s, timestamp_sec = %s, updated_at = NOW()
            WHERE id = %s AND user_sub = %s
            RETURNING id, user_sub, course_id, lesson_id, body, timestamp_sec,
                      created_at, updated_at
            """,
            (body, timestamp_sec, note_id, user_sub),
            commit=True,
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("update_note returned no row")
        return _row_from_db(row)

    def delete_note(self, *, note_id: str, user_sub: str) -> bool:
        cur = self._execute(
            """
            DELETE FROM lesson_notes
            WHERE id = %s AND user_sub = %s
            """,
            (note_id, user_sub),
            commit=True,
        )
        return cur.rowcount > 0
