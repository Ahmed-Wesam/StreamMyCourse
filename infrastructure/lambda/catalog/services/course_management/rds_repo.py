"""PostgreSQL adapter for ``CourseCatalogRepositoryPort``.

Mirrors the public surface of ``services.course_management.repo.CourseCatalogRepository``
(the DynamoDB implementation) so the rest of the stack sees the same behavior
when ``USE_RDS=true``.

Mapping rules:
  * Column names: ``snake_case`` in SQL, ``camelCase`` in the domain model
    (``created_at`` <-> ``createdAt``, ``thumbnail_key`` <-> ``thumbnailKey``,
    etc.).  All translation happens in the private ``_row_to_*`` helpers.
  * Identifiers: SQL uses ``UUID PRIMARY KEY`` but ``Course.id`` / ``Lesson.id``
    are ``str``. psycopg2 returns ``uuid.UUID`` objects for UUID columns, so
    the helpers cast with ``str(...)`` before construction.
  * Timestamps: SQL uses ``TIMESTAMPTZ``; domain models carry ISO-8601 strings.
    datetime values returned by psycopg2 are rendered with ``.isoformat()``.

Every query uses parameterized ``%s`` placeholders -- user input is never
formatted into the SQL string (SQL-injection safe).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

try:  # pragma: no cover - optional dependency path
    import psycopg2
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]

from services.common.errors import Conflict
from services.course_management.models import Course, Lesson


logger = logging.getLogger(__name__)


ConnectionFactory = Callable[[], Any]


def _to_iso(value: Any) -> str:
    """Render TIMESTAMPTZ rows as ISO strings; leave anything else as-is."""
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return str(value)


def _row_to_course(row: Tuple[Any, ...]) -> Course:
    """Map a ``courses`` row tuple to the camelCase domain type.

    Column order must match the SELECT used by all query sites in this module::

        id, title, description, status, created_by, thumbnail_key, created_at, updated_at
    """
    (cid, title, description, status, created_by, thumbnail_key, created_at, updated_at) = row
    return Course(
        id=str(cid),
        title=str(title or ""),
        description=str(description or ""),
        status=str(status or "DRAFT"),
        createdAt=_to_iso(created_at),
        updatedAt=_to_iso(updated_at),
        thumbnailKey=str(thumbnail_key or ""),
        createdBy=str(created_by or ""),
    )


def _row_to_lesson(row: Tuple[Any, ...]) -> Lesson:
    """Map a ``lessons`` row tuple to the camelCase domain type.

    Column order must match every SELECT in this module::

        id, title, lesson_order, video_key, video_status, thumbnail_key, duration
    """
    (lid, title, lesson_order, video_key, video_status, thumbnail_key, duration) = row
    return Lesson(
        id=str(lid),
        title=str(title or ""),
        order=int(lesson_order or 0),
        videoKey=str(video_key or ""),
        videoStatus=str(video_status or "pending"),
        duration=int(duration or 0),
        thumbnailKey=str(thumbnail_key or ""),
    )


_COURSE_COLUMNS = (
    "id, title, description, status, created_by, thumbnail_key, created_at, updated_at"
)
_LESSON_COLUMNS = (
    "id, title, lesson_order, video_key, video_status, thumbnail_key, duration"
)


class CourseCatalogRdsRepository:
    """PostgreSQL implementation of :class:`CourseCatalogRepositoryPort`.

    The constructor takes a **connection factory** rather than a connection so
    it can be shared between Lambda invocations (cached by ``bootstrap``) and
    reconnected transparently on ``OperationalError``. The factory is only
    invoked lazily, on the first query, and the connection is cached for the
    lifetime of the warm container.
    """

    def __init__(self, conn_factory: ConnectionFactory) -> None:
        self._conn_factory = conn_factory
        self._conn: Optional[Any] = None

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def _connection(self) -> Any:
        if self._conn is None:
            self._conn = self._conn_factory()
        return self._conn

    def _execute(
        self, sql: str, params: Tuple[Any, ...] = (), *, commit: bool = False
    ) -> Any:
        """Run a single statement and return the cursor (for fetch*/rowcount).

        On a stale/dropped connection (``psycopg2.OperationalError``) the cached
        connection is discarded and the statement retried once against a fresh
        connection. This handles RDS idle timeouts and cross-region network
        blips without bubbling a 500 to the user on the first failure.
        """
        try:
            conn = self._connection()
            cur = conn.cursor()
            cur.execute(sql, params)
            if commit:
                conn.commit()
            return cur
        except Exception as exc:  # broad so the retry covers any driver re-raise
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

    # ------------------------------------------------------------------
    # Course queries
    # ------------------------------------------------------------------
    def list_courses(self) -> List[Course]:
        cur = self._execute(f"SELECT {_COURSE_COLUMNS} FROM courses ORDER BY created_at")
        return [_row_to_course(row) for row in cur.fetchall()]

    def list_courses_by_instructor(self, created_by: str) -> List[Course]:
        cb = (created_by or "").strip()
        if not cb:
            return []
        cur = self._execute(
            f"SELECT {_COURSE_COLUMNS} FROM courses WHERE created_by = %s ORDER BY created_at ASC",
            (cb,),
        )
        return [_row_to_course(row) for row in cur.fetchall()]

    def get_course(self, course_id: str) -> Optional[Course]:
        cur = self._execute(
            f"SELECT {_COURSE_COLUMNS} FROM courses WHERE id = %s",
            (course_id,),
        )
        row = cur.fetchone()
        return _row_to_course(row) if row else None

    def create_course(
        self, title: str, description: str, *, created_by: str = ""
    ) -> Course:
        cur = self._execute(
            f"""
            INSERT INTO courses (title, description, status, created_by)
            VALUES (%s, %s, %s, %s)
            RETURNING {_COURSE_COLUMNS}
            """,
            (title, description, "DRAFT", (created_by or "").strip()),
            commit=True,
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("INSERT courses ... RETURNING returned no row")
        return _row_to_course(row)

    def update_course(self, course_id: str, title: str, description: str) -> None:
        self._execute(
            "UPDATE courses SET title = %s, description = %s, updated_at = NOW() WHERE id = %s",
            (title, description, course_id),
            commit=True,
        )

    def set_course_status(self, course_id: str, status: str) -> None:
        self._execute(
            "UPDATE courses SET status = %s, updated_at = NOW() WHERE id = %s",
            (status, course_id),
            commit=True,
        )

    def set_course_thumbnail(self, course_id: str, thumbnail_key: str) -> None:
        self._execute(
            "UPDATE courses SET thumbnail_key = %s, updated_at = NOW() WHERE id = %s",
            (thumbnail_key, course_id),
            commit=True,
        )

    def delete_course_and_lessons(self, course_id: str) -> None:
        # enrollments.course_id and lessons.course_id use ON DELETE CASCADE from courses.
        self._execute(
            "DELETE FROM courses WHERE id = %s",
            (course_id,),
            commit=True,
        )

    # ------------------------------------------------------------------
    # Lesson queries
    # ------------------------------------------------------------------
    def list_lessons(self, course_id: str) -> List[Lesson]:
        cur = self._execute(
            f"SELECT {_LESSON_COLUMNS} FROM lessons WHERE course_id = %s ORDER BY lesson_order",
            (course_id,),
        )
        return [_row_to_lesson(row) for row in cur.fetchall()]

    def get_lesson_by_id(self, course_id: str, lesson_id: str) -> Optional[Lesson]:
        cur = self._execute(
            f"SELECT {_LESSON_COLUMNS} FROM lessons WHERE course_id = %s AND id = %s",
            (course_id, lesson_id),
        )
        row = cur.fetchone()
        return _row_to_lesson(row) if row else None

    def create_lesson(self, course_id: str, title: str) -> Lesson:
        # Order = MAX(lesson_order) + 1. A separate SELECT keeps the INSERT
        # simple (no CTE) and matches the DynamoDB implementation's contract.
        cur = self._execute(
            "SELECT COALESCE(MAX(lesson_order), 0) FROM lessons WHERE course_id = %s",
            (course_id,),
        )
        row = cur.fetchone()
        next_order = int((row[0] if row else 0) or 0) + 1

        cur = self._execute(
            f"""
            INSERT INTO lessons (course_id, title, lesson_order)
            VALUES (%s, %s, %s)
            RETURNING {_LESSON_COLUMNS}
            """,
            (course_id, title, next_order),
            commit=True,
        )
        created = cur.fetchone()
        if created is None:
            raise RuntimeError("INSERT lessons ... RETURNING returned no row")
        return _row_to_lesson(created)

    def update_lesson_title(
        self, course_id: str, lesson_id: str, title: str
    ) -> None:
        self._execute(
            "UPDATE lessons SET title = %s WHERE course_id = %s AND id = %s",
            (title, course_id, lesson_id),
            commit=True,
        )

    def delete_lesson(self, course_id: str, lesson_id: str) -> None:
        self._execute(
            "DELETE FROM lessons WHERE course_id = %s AND id = %s",
            (course_id, lesson_id),
            commit=True,
        )

    def set_lesson_video(
        self, course_id: str, lesson_id: str, video_key: str, status: str
    ) -> None:
        self._execute(
            """
            UPDATE lessons
               SET video_key = %s,
                   video_status = %s
             WHERE course_id = %s AND id = %s
            """,
            (video_key, status, course_id, lesson_id),
            commit=True,
        )

    def set_lesson_video_if_video_key_matches(
        self,
        course_id: str,
        lesson_id: str,
        video_key: str,
        status: str,
        *,
        expected_video_key: str,
    ) -> None:
        """Atomically swap video_key iff the stored value matches expected.

        Translates the DynamoDB ``ConditionExpression`` pattern to a SQL
        predicate. When the condition is not met (another upload raced us),
        ``rowcount`` is 0 and we raise :class:`Conflict` so the service layer
        can clean up the presigned key on S3.
        """
        cur = self._execute(
            """
            UPDATE lessons
               SET video_key = %s,
                   video_status = %s
             WHERE course_id = %s
               AND id = %s
               AND video_key = %s
            """,
            (video_key, status, course_id, lesson_id, expected_video_key),
            commit=True,
        )
        if getattr(cur, "rowcount", 0) == 0:
            raise Conflict("Another upload started for this lesson; retry.")

    def set_lesson_video_status(
        self, course_id: str, lesson_id: str, status: str
    ) -> None:
        self._execute(
            "UPDATE lessons SET video_status = %s WHERE course_id = %s AND id = %s",
            (status, course_id, lesson_id),
            commit=True,
        )

    def set_lesson_thumbnail(
        self, course_id: str, lesson_id: str, thumbnail_key: str
    ) -> None:
        self._execute(
            "UPDATE lessons SET thumbnail_key = %s WHERE course_id = %s AND id = %s",
            (thumbnail_key, course_id, lesson_id),
            commit=True,
        )

    def set_lesson_orders(self, course_id: str, orders: Dict[str, int]) -> None:
        """Renumber lessons transactionally.

        A single transaction spans every UPDATE so the on-disk state never
        contains partial reordering. ``UNIQUE (course_id, lesson_order)`` on
        the table prevents two rows from colliding on the same order inside
        the transaction.
        """
        if not orders:
            return
        conn = self._connection()
        try:
            cur = conn.cursor()
            for lesson_id, order in orders.items():
                cur.execute(
                    "UPDATE lessons SET lesson_order = %s WHERE course_id = %s AND id = %s",
                    (int(order), course_id, lesson_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
