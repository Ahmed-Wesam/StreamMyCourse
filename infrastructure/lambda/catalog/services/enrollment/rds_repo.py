"""PostgreSQL adapter for :class:`EnrollmentRepositoryPort`.

Mirrors :class:`services.enrollment.repo.EnrollmentRepository` (DynamoDB) so
that flipping ``USE_RDS`` has no observable effect on the service layer.

``enrollments`` has ``PRIMARY KEY (user_sub, course_id)``, so idempotent upserts
use ``ON CONFLICT DO NOTHING`` -- a second enrollment attempt is a no-op just
like the DynamoDB ``PutItem`` overwrite semantics.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

try:  # pragma: no cover - optional dependency path
    import psycopg2
except Exception:  # pragma: no cover - surface at first DB call instead
    psycopg2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


ConnectionFactory = Callable[[], Any]


class EnrollmentRdsRepository:
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
                logger.warning("RDS connection lost, reconnecting and retrying once: %s", exc)
                self._conn = None
                conn = self._connection()
                cur = conn.cursor()
                cur.execute(sql, params)
                if commit:
                    conn.commit()
                return cur
            raise

    def has_enrollment(self, *, user_sub: str, course_id: str) -> bool:
        # SELECT 1 is cheaper than fetching columns we will not read.
        cur = self._execute(
            "SELECT 1 FROM enrollments WHERE user_sub = %s AND course_id = %s",
            (user_sub, course_id),
        )
        return cur.fetchone() is not None

    def put_enrollment(
        self, *, user_sub: str, course_id: str, source: str = "self_service"
    ) -> None:
        self._execute(
            """
            INSERT INTO enrollments (user_sub, course_id, source)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_sub, course_id) DO NOTHING
            """,
            (user_sub, course_id, source),
            commit=True,
        )
