"""PostgreSQL adapter for research team (RS-14)."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

from services.common.errors import Conflict
from services.research_team.ports import (
    ApplicationRow,
    RequiredCourseRow,
    ResearchTeamRepositoryPort,
)

try:  # pragma: no cover
    import psycopg2
    from psycopg2 import errorcodes
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]
    errorcodes = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]

_SELECT_COLS = """
    id, user_sub, status, reapply_allowed, submitted_at,
    full_name, email, country, institution, position,
    publication_count, project_count, stats_experience, sys_review_experience,
    research_areas, interests, motivation, weekly_hours, acknowledged_at
"""

_OPEN_INDEX_HINT = "research_team_applications_one_open"
_ACCEPTED_INDEX_HINT = "research_team_applications_one_accepted"


def _areas_from_db(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        return tuple(str(v) for v in value)
    if isinstance(value, tuple):
        return tuple(str(v) for v in value)
    return ()


def _row_from_db(row: tuple) -> ApplicationRow:
    return ApplicationRow(
        id=str(row[0]),
        user_sub=str(row[1]),
        status=str(row[2]),
        reapply_allowed=bool(row[3]),
        submitted_at=row[4],
        full_name=str(row[5]),
        email=str(row[6]),
        country=str(row[7]),
        institution=str(row[8]),
        position=str(row[9]),
        publication_count=int(row[10]),
        project_count=int(row[11]),
        stats_experience=str(row[12]),
        sys_review_experience=str(row[13]),
        research_areas=_areas_from_db(row[14]),
        interests=str(row[15]),
        motivation=str(row[16]),
        weekly_hours=str(row[17]),
        acknowledged_at=row[18],
    )


class ResearchTeamRdsRepository(ResearchTeamRepositoryPort):
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

    def _unique_user_status_conflict(self, exc: BaseException) -> Optional[Conflict]:
        if psycopg2 is None or errorcodes is None:
            return None
        if not isinstance(exc, psycopg2.IntegrityError):
            return None
        if getattr(exc, "pgcode", None) != errorcodes.UNIQUE_VIOLATION:
            return None
        diag = getattr(exc, "diag", None)
        constraint = str(getattr(diag, "constraint_name", None) or "")
        message = str(exc)
        if _OPEN_INDEX_HINT in constraint or _OPEN_INDEX_HINT in message:
            return Conflict("Application already open", code="application_open")
        if _ACCEPTED_INDEX_HINT in constraint or _ACCEPTED_INDEX_HINT in message:
            return Conflict("Student already accepted", code="already_accepted")
        return None

    def list_required_published_courses(self) -> List[RequiredCourseRow]:
        cur = self._execute(
            """
            SELECT r.course_id, c.title
              FROM research_team_required_courses r
              JOIN courses c ON c.id = r.course_id
             WHERE c.status = 'PUBLISHED'
             ORDER BY c.title ASC, r.course_id ASC
            """
        )
        return [
            RequiredCourseRow(course_id=str(r[0]), title=str(r[1]))
            for r in cur.fetchall()
        ]

    def set_requirement(self, course_id: str, *, required: bool) -> None:
        if required:
            self._execute(
                """
                INSERT INTO research_team_required_courses (course_id)
                VALUES (%s)
                ON CONFLICT (course_id) DO NOTHING
                """,
                (course_id,),
                commit=True,
            )
        else:
            self._execute(
                "DELETE FROM research_team_required_courses WHERE course_id = %s",
                (course_id,),
                commit=True,
            )

    def is_required(self, course_id: str) -> bool:
        cur = self._execute(
            "SELECT 1 FROM research_team_required_courses WHERE course_id = %s",
            (course_id,),
        )
        return cur.fetchone() is not None

    def course_exists(self, course_id: str) -> bool:
        cur = self._execute("SELECT 1 FROM courses WHERE id = %s", (course_id,))
        return cur.fetchone() is not None

    def get_application(self, application_id: str) -> Optional[ApplicationRow]:
        cur = self._execute(
            f"SELECT {_SELECT_COLS} FROM research_team_applications WHERE id = %s",
            (application_id,),
        )
        row = cur.fetchone()
        return _row_from_db(row) if row else None

    def list_applications(self) -> List[ApplicationRow]:
        cur = self._execute(
            f"""
            SELECT {_SELECT_COLS}
              FROM research_team_applications
             ORDER BY submitted_at DESC, id DESC
            """
        )
        return [_row_from_db(r) for r in cur.fetchall()]

    def get_latest_for_user(self, user_sub: str) -> Optional[ApplicationRow]:
        cur = self._execute(
            f"""
            SELECT {_SELECT_COLS}
              FROM research_team_applications
             WHERE user_sub = %s
             ORDER BY submitted_at DESC, id DESC
             LIMIT 1
            """,
            (user_sub,),
        )
        row = cur.fetchone()
        return _row_from_db(row) if row else None

    def has_accepted(self, user_sub: str) -> bool:
        cur = self._execute(
            """
            SELECT 1 FROM research_team_applications
             WHERE user_sub = %s AND status = 'accepted'
             LIMIT 1
            """,
            (user_sub,),
        )
        return cur.fetchone() is not None

    def has_open(self, user_sub: str) -> bool:
        cur = self._execute(
            """
            SELECT 1 FROM research_team_applications
             WHERE user_sub = %s AND status IN ('submitted', 'under_review')
             LIMIT 1
            """,
            (user_sub,),
        )
        return cur.fetchone() is not None

    def insert_application(self, row: ApplicationRow) -> ApplicationRow:
        areas = list(row.research_areas)
        try:
            cur = self._execute(
                f"""
                INSERT INTO research_team_applications (
                    id, user_sub, status, reapply_allowed, submitted_at,
                    full_name, email, country, institution, position,
                    publication_count, project_count, stats_experience, sys_review_experience,
                    research_areas, interests, motivation, weekly_hours, acknowledged_at
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                RETURNING {_SELECT_COLS}
                """,
                (
                    row.id,
                    row.user_sub,
                    row.status,
                    row.reapply_allowed,
                    row.submitted_at,
                    row.full_name,
                    row.email,
                    row.country,
                    row.institution,
                    row.position,
                    row.publication_count,
                    row.project_count,
                    row.stats_experience,
                    row.sys_review_experience,
                    areas,
                    row.interests,
                    row.motivation,
                    row.weekly_hours,
                    row.acknowledged_at,
                ),
                commit=True,
            )
            fetched = cur.fetchone()
            if fetched is None:
                raise RuntimeError("INSERT research_team_applications returned no row")
            return _row_from_db(fetched)
        except Exception as exc:
            conflict = self._unique_user_status_conflict(exc)
            if conflict is not None:
                raise conflict from exc
            raise

    def update_status(self, application_id: str, status: str) -> ApplicationRow:
        try:
            cur = self._execute(
                f"""
                UPDATE research_team_applications
                   SET status = %s
                 WHERE id = %s
             RETURNING {_SELECT_COLS}
                """,
                (status, application_id),
                commit=True,
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError(f"update_status target missing: {application_id}")
            return _row_from_db(row)
        except Exception as exc:
            conflict = self._unique_user_status_conflict(exc)
            if conflict is not None:
                raise conflict from exc
            raise

    def set_reapply_allowed(self, application_id: str, *, allowed: bool) -> ApplicationRow:
        cur = self._execute(
            f"""
            UPDATE research_team_applications
               SET reapply_allowed = %s
             WHERE id = %s
         RETURNING {_SELECT_COLS}
            """,
            (allowed, application_id),
            commit=True,
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError(f"set_reapply_allowed target missing: {application_id}")
        return _row_from_db(row)
