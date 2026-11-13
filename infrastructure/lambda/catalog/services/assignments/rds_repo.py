"""PostgreSQL adapter for :class:`AssignmentsRepositoryPort`."""

from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional, Sequence

from services.common.db_tx import delete_in_batches, run_transaction
from services.common.errors import Conflict
from services.assignments.ports import (
    AssignmentRow,
    AssignmentsRepositoryPort,
    CriterionRow,
    GradeRow,
    GradeScoreRow,
    SubmissionFileRow,
    SubmissionRow,
)

try:  # pragma: no cover
    import psycopg2
except Exception:  # pragma: no cover
    psycopg2 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

ConnectionFactory = Callable[[], Any]


def _criterion_from_db(row: tuple) -> CriterionRow:
    return CriterionRow(
        id=str(row[0]),
        assignment_id=str(row[1]),
        label=row[2],
        max_points=int(row[3]),
        sort_order=int(row[4]),
    )


def _assignment_from_db(row: tuple, criteria: tuple[CriterionRow, ...] = ()) -> AssignmentRow:
    return AssignmentRow(
        id=str(row[0]),
        course_id=str(row[1]),
        module_id=str(row[2]),
        title=row[3],
        status=row[4],
        pass_percent=int(row[5]),
        counts_toward_certificate=bool(row[6]),
        instructions_mode=row[7],
        instructions_text=row[8] or "",
        instructions_html=row[9] or "",
        instructions_image_key=row[10] or "",
        instructions_image_ready=bool(row[11]),
        rubric_mode=row[12],
        rubric_text=row[13] or "",
        rubric_html=row[14] or "",
        rubric_image_key=row[15] or "",
        rubric_image_ready=bool(row[16]),
        created_at=row[17],
        updated_at=row[18],
        criteria=criteria,
    )


_ASSIGNMENT_SELECT = """
    SELECT id, course_id, module_id, title, status, pass_percent,
           counts_toward_certificate,
           instructions_mode, instructions_text, instructions_html,
           instructions_image_key, instructions_image_ready,
           rubric_mode, rubric_text, rubric_html,
           rubric_image_key, rubric_image_ready,
           created_at, updated_at
    FROM assignments
"""

_DELETE_ASSIGNMENT_GRADE_SCORES_FOR_USER_SQL = """
DELETE FROM assignment_grade_scores AS t
USING (
    SELECT gs.grade_id, gs.criterion_id
    FROM assignment_grade_scores gs
    INNER JOIN assignment_grades g ON g.id = gs.grade_id
    INNER JOIN assignment_submissions s ON s.id = g.submission_id
    WHERE s.user_sub = %s
    LIMIT 1000
) AS batch
WHERE t.grade_id = batch.grade_id AND t.criterion_id = batch.criterion_id
"""
_DELETE_ASSIGNMENT_GRADES_FOR_USER_SQL = """
DELETE FROM assignment_grades AS t
USING (
    SELECT g.id
    FROM assignment_grades g
    INNER JOIN assignment_submissions s ON s.id = g.submission_id
    WHERE s.user_sub = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_USER_SQL = """
DELETE FROM assignment_submission_files AS t
USING (
    SELECT f.id
    FROM assignment_submission_files f
    INNER JOIN assignment_submissions s ON s.id = f.submission_id
    WHERE s.user_sub = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSIONS_FOR_USER_SQL = """
DELETE FROM assignment_submissions AS t
USING (
    SELECT id FROM assignment_submissions
    WHERE user_sub = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_GRADE_SCORES_FOR_COURSE_SQL = """
DELETE FROM assignment_grade_scores AS t
USING (
    SELECT gs.grade_id, gs.criterion_id
    FROM assignment_grade_scores gs
    INNER JOIN assignment_grades g ON g.id = gs.grade_id
    WHERE g.course_id = %s
    LIMIT 1000
) AS batch
WHERE t.grade_id = batch.grade_id AND t.criterion_id = batch.criterion_id
"""
_DELETE_ASSIGNMENT_GRADES_FOR_COURSE_SQL = """
DELETE FROM assignment_grades AS t
USING (
    SELECT id FROM assignment_grades
    WHERE course_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_COURSE_SQL = """
DELETE FROM assignment_submission_files AS t
USING (
    SELECT id FROM assignment_submission_files
    WHERE course_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSIONS_FOR_COURSE_SQL = """
DELETE FROM assignment_submissions AS t
USING (
    SELECT id FROM assignment_submissions
    WHERE course_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_GRADE_SCORES_FOR_MODULE_SQL = """
DELETE FROM assignment_grade_scores AS t
USING (
    SELECT gs.grade_id, gs.criterion_id
    FROM assignment_grade_scores gs
    INNER JOIN assignment_grades g ON g.id = gs.grade_id
    INNER JOIN assignment_submissions s ON s.id = g.submission_id
    INNER JOIN assignments a ON a.id = s.assignment_id
    WHERE a.course_id = %s AND a.module_id = %s
    LIMIT 1000
) AS batch
WHERE t.grade_id = batch.grade_id AND t.criterion_id = batch.criterion_id
"""
_DELETE_ASSIGNMENT_GRADES_FOR_MODULE_SQL = """
DELETE FROM assignment_grades AS t
USING (
    SELECT g.id
    FROM assignment_grades g
    INNER JOIN assignment_submissions s ON s.id = g.submission_id
    INNER JOIN assignments a ON a.id = s.assignment_id
    WHERE a.course_id = %s AND a.module_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_MODULE_SQL = """
DELETE FROM assignment_submission_files AS t
USING (
    SELECT f.id
    FROM assignment_submission_files f
    INNER JOIN assignments a ON a.id = f.assignment_id
    WHERE a.course_id = %s AND a.module_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSIONS_FOR_MODULE_SQL = """
DELETE FROM assignment_submissions AS t
USING (
    SELECT s.id
    FROM assignment_submissions s
    INNER JOIN assignments a ON a.id = s.assignment_id
    WHERE a.course_id = %s AND a.module_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_GRADE_SCORES_FOR_ASSIGNMENT_SQL = """
DELETE FROM assignment_grade_scores AS t
USING (
    SELECT gs.grade_id, gs.criterion_id
    FROM assignment_grade_scores gs
    INNER JOIN assignment_grades g ON g.id = gs.grade_id
    WHERE g.assignment_id = %s
    LIMIT 1000
) AS batch
WHERE t.grade_id = batch.grade_id AND t.criterion_id = batch.criterion_id
"""
_DELETE_ASSIGNMENT_GRADES_FOR_ASSIGNMENT_SQL = """
DELETE FROM assignment_grades AS t
USING (
    SELECT id FROM assignment_grades
    WHERE assignment_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_ASSIGNMENT_SQL = """
DELETE FROM assignment_submission_files AS t
USING (
    SELECT id FROM assignment_submission_files
    WHERE assignment_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""
_DELETE_ASSIGNMENT_SUBMISSIONS_FOR_ASSIGNMENT_SQL = """
DELETE FROM assignment_submissions AS t
USING (
    SELECT id FROM assignment_submissions
    WHERE assignment_id = %s
    LIMIT 1000
) AS batch
WHERE t.id = batch.id
"""

_SUBMISSION_ROW_SELECT = """
    SELECT id, assignment_id, course_id, user_sub, status, note,
           created_at, updated_at, submitted_at
    FROM assignment_submissions
"""


class AssignmentsRdsRepository(AssignmentsRepositoryPort):
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

    def _load_criteria(self, assignment_id: str) -> tuple[CriterionRow, ...]:
        cur = self._execute(
            """
            SELECT id, assignment_id, label, max_points, sort_order
            FROM assignment_criteria
            WHERE assignment_id = %s
            ORDER BY sort_order ASC, id ASC
            """,
            (assignment_id,),
        )
        return tuple(_criterion_from_db(r) for r in cur.fetchall())

    def count_assignments_for_course(self, course_id: str) -> int:
        cur = self._execute(
            "SELECT COUNT(*) FROM assignments WHERE course_id = %s",
            (course_id,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def list_assignments(
        self, course_id: str, *, published_only: bool = False
    ) -> List[AssignmentRow]:
        if published_only:
            cur = self._execute(
                _ASSIGNMENT_SELECT
                + " WHERE course_id = %s AND status = 'published' ORDER BY created_at ASC",
                (course_id,),
            )
        else:
            cur = self._execute(
                _ASSIGNMENT_SELECT
                + " WHERE course_id = %s ORDER BY created_at ASC",
                (course_id,),
            )
        out: list[AssignmentRow] = []
        for r in cur.fetchall():
            criteria = self._load_criteria(str(r[0]))
            out.append(_assignment_from_db(r, criteria))
        return out

    def get_assignment(
        self, course_id: str, assignment_id: str
    ) -> Optional[AssignmentRow]:
        cur = self._execute(
            _ASSIGNMENT_SELECT + " WHERE course_id = %s AND id = %s",
            (course_id, assignment_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return _assignment_from_db(row, self._load_criteria(assignment_id))

    def insert_assignment(
        self,
        *,
        course_id: str,
        module_id: str,
        title: str,
        pass_percent: int,
        counts_toward_certificate: bool,
        status: str = "draft",
    ) -> AssignmentRow:
        conn = self._connection()

        def body() -> AssignmentRow:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO assignments (
                    course_id, module_id, title, status, pass_percent,
                    counts_toward_certificate
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, course_id, module_id, title, status, pass_percent,
                          counts_toward_certificate,
                          instructions_mode, instructions_text, instructions_html,
                          instructions_image_key, instructions_image_ready,
                          rubric_mode, rubric_text, rubric_html,
                          rubric_image_key, rubric_image_ready,
                          created_at, updated_at
                """,
                (
                    course_id,
                    module_id,
                    title,
                    status,
                    pass_percent,
                    counts_toward_certificate,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("insert_assignment returned no row")
            return _assignment_from_db(row, ())

        return run_transaction(conn, body)

    def update_assignment(self, row: AssignmentRow) -> AssignmentRow:
        conn = self._connection()

        def body() -> AssignmentRow:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE assignments SET
                    module_id = %s,
                    title = %s,
                    status = %s,
                    pass_percent = %s,
                    counts_toward_certificate = %s,
                    instructions_mode = %s,
                    instructions_text = %s,
                    instructions_html = %s,
                    instructions_image_key = %s,
                    instructions_image_ready = %s,
                    rubric_mode = %s,
                    rubric_text = %s,
                    rubric_html = %s,
                    rubric_image_key = %s,
                    rubric_image_ready = %s,
                    updated_at = NOW()
                WHERE id = %s AND course_id = %s
                RETURNING id, course_id, module_id, title, status, pass_percent,
                          counts_toward_certificate,
                          instructions_mode, instructions_text, instructions_html,
                          instructions_image_key, instructions_image_ready,
                          rubric_mode, rubric_text, rubric_html,
                          rubric_image_key, rubric_image_ready,
                          created_at, updated_at
                """,
                (
                    row.module_id,
                    row.title,
                    row.status,
                    row.pass_percent,
                    row.counts_toward_certificate,
                    row.instructions_mode,
                    row.instructions_text,
                    row.instructions_html,
                    row.instructions_image_key,
                    row.instructions_image_ready,
                    row.rubric_mode,
                    row.rubric_text,
                    row.rubric_html,
                    row.rubric_image_key,
                    row.rubric_image_ready,
                    row.id,
                    row.course_id,
                ),
            )
            db_row = cur.fetchone()
            if db_row is None:
                raise RuntimeError("update_assignment returned no row")
            return _assignment_from_db(db_row, self._load_criteria(row.id))

        return run_transaction(conn, body)

    def _delete_assignment_children(self, assignment_id: str) -> None:
        self._batched_delete(
            _DELETE_ASSIGNMENT_GRADE_SCORES_FOR_ASSIGNMENT_SQL, (assignment_id,)
        )
        self._batched_delete(
            _DELETE_ASSIGNMENT_GRADES_FOR_ASSIGNMENT_SQL, (assignment_id,)
        )
        self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_ASSIGNMENT_SQL, (assignment_id,)
        )
        self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSIONS_FOR_ASSIGNMENT_SQL, (assignment_id,)
        )

    def delete_assignment(self, course_id: str, assignment_id: str) -> bool:
        self._delete_assignment_children(assignment_id)
        conn = self._connection()

        def body() -> bool:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM assignments WHERE course_id = %s AND id = %s",
                (course_id, assignment_id),
            )
            return cur.rowcount > 0

        return run_transaction(conn, body)

    def list_object_keys_for_assignment(
        self, course_id: str, assignment_id: str
    ) -> List[str]:
        cur = self._execute(
            """
            SELECT instructions_image_key, rubric_image_key
            FROM assignments
            WHERE course_id = %s AND id = %s
            """,
            (course_id, assignment_id),
        )
        row = cur.fetchone()
        keys: list[str] = []
        if row:
            if row[0]:
                keys.append(row[0])
            if row[1]:
                keys.append(row[1])
        cur = self._execute(
            """
            SELECT object_key FROM assignment_submission_files
            WHERE course_id = %s AND assignment_id = %s AND object_key <> ''
            """,
            (course_id, assignment_id),
        )
        keys.extend(r[0] for r in cur.fetchall() if r[0])
        return keys

    def list_object_keys_for_course(self, course_id: str) -> List[str]:
        cur = self._execute(
            """
            SELECT instructions_image_key, rubric_image_key
            FROM assignments
            WHERE course_id = %s
            """,
            (course_id,),
        )
        keys: list[str] = []
        for row in cur.fetchall():
            if row[0]:
                keys.append(row[0])
            if row[1]:
                keys.append(row[1])
        cur = self._execute(
            """
            SELECT object_key FROM assignment_submission_files
            WHERE course_id = %s AND object_key <> ''
            """,
            (course_id,),
        )
        keys.extend(r[0] for r in cur.fetchall() if r[0])
        return keys

    def list_object_keys_for_module(self, course_id: str, module_id: str) -> List[str]:
        cur = self._execute(
            """
            SELECT instructions_image_key, rubric_image_key
            FROM assignments
            WHERE course_id = %s AND module_id = %s
            """,
            (course_id, module_id),
        )
        keys: list[str] = []
        for row in cur.fetchall():
            if row[0]:
                keys.append(row[0])
            if row[1]:
                keys.append(row[1])
        cur = self._execute(
            """
            SELECT f.object_key
            FROM assignment_submission_files f
            INNER JOIN assignments a ON a.id = f.assignment_id
            WHERE a.course_id = %s AND a.module_id = %s AND f.object_key <> ''
            """,
            (course_id, module_id),
        )
        keys.extend(r[0] for r in cur.fetchall() if r[0])
        return keys

    def list_submission_file_keys_for_user(
        self, user_sub: str
    ) -> List[tuple[str, str]]:
        cur = self._execute(
            """
            SELECT f.course_id, f.object_key
            FROM assignment_submission_files f
            INNER JOIN assignment_submissions s ON s.id = f.submission_id
            WHERE s.user_sub = %s AND f.object_key <> ''
            """,
            (user_sub,),
        )
        return [(str(r[0]), str(r[1])) for r in cur.fetchall() if r[1]]

    def replace_criteria(
        self,
        *,
        assignment_id: str,
        criteria: Sequence[tuple[str, str, int]],
    ) -> List[CriterionRow]:
        conn = self._connection()

        def body() -> List[CriterionRow]:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id FROM assignments
                WHERE id = %s
                FOR UPDATE
                """,
                (assignment_id,),
            )
            if cur.fetchone() is None:
                raise RuntimeError("replace_criteria: assignment not found")
            cur.execute(
                "DELETE FROM assignment_criteria WHERE assignment_id = %s",
                (assignment_id,),
            )
            out: list[CriterionRow] = []
            for i, (cid, label, max_points) in enumerate(criteria):
                cur.execute(
                    """
                    INSERT INTO assignment_criteria (
                        id, assignment_id, label, max_points, sort_order
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, assignment_id, label, max_points, sort_order
                    """,
                    (cid, assignment_id, label, max_points, i),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("replace_criteria insert returned no row")
                out.append(_criterion_from_db(row))
            return out

        return run_transaction(conn, body)

    def list_criteria(self, assignment_id: str) -> List[CriterionRow]:
        return list(self._load_criteria(assignment_id))

    def _file_from_db(self, row: tuple) -> SubmissionFileRow:
        return SubmissionFileRow(
            id=str(row[0]),
            submission_id=str(row[1]),
            assignment_id=str(row[2]),
            course_id=str(row[3]),
            title=row[4],
            file_type=row[5],
            object_key=row[6] or "",
            content_type=row[7] or "",
            byte_size=int(row[8]),
            status=row[9],
            created_at=row[10],
        )

    def _grade_from_db(self, row: tuple, scores: tuple[GradeScoreRow, ...]) -> GradeRow:
        return GradeRow(
            id=str(row[0]),
            submission_id=str(row[1]),
            assignment_id=str(row[2]),
            course_id=str(row[3]),
            score_percent=int(row[4]),
            pass_percent=int(row[5]),
            passed=bool(row[6]),
            feedback=row[7],
            graded_by=row[8],
            graded_at=row[9],
            scores=scores,
        )

    def _load_grade(self, submission_id: str) -> Optional[GradeRow]:
        cur = self._execute(
            """
            SELECT id, submission_id, assignment_id, course_id,
                   score_percent, pass_percent, passed, feedback,
                   graded_by, graded_at
            FROM assignment_grades
            WHERE submission_id = %s
            """,
            (submission_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cur2 = self._execute(
            """
            SELECT criterion_id, points
            FROM assignment_grade_scores
            WHERE grade_id = %s
            """,
            (row[0],),
        )
        scores = tuple(
            GradeScoreRow(criterion_id=str(r[0]), points=int(r[1]))
            for r in cur2.fetchall()
        )
        return self._grade_from_db(row, scores)

    def _load_files(self, submission_id: str) -> tuple[SubmissionFileRow, ...]:
        cur = self._execute(
            """
            SELECT id, submission_id, assignment_id, course_id, title, file_type,
                   object_key, content_type, byte_size, status, created_at
            FROM assignment_submission_files
            WHERE submission_id = %s
            ORDER BY created_at ASC
            """,
            (submission_id,),
        )
        return tuple(self._file_from_db(r) for r in cur.fetchall())

    def _submission_from_db(self, row: tuple) -> SubmissionRow:
        sid = str(row[0])
        return SubmissionRow(
            id=sid,
            assignment_id=str(row[1]),
            course_id=str(row[2]),
            user_sub=row[3],
            status=row[4],
            note=row[5] or "",
            created_at=row[6],
            updated_at=row[7],
            submitted_at=row[8],
            files=self._load_files(sid),
            grade=self._load_grade(sid),
        )

    def get_latest_submission_for_user(
        self, *, assignment_id: str, user_sub: str
    ) -> Optional[SubmissionRow]:
        cur = self._execute(
            """
            SELECT id, assignment_id, course_id, user_sub, status, note,
                   created_at, updated_at, submitted_at
            FROM assignment_submissions
            WHERE assignment_id = %s AND user_sub = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (assignment_id, user_sub),
        )
        row = cur.fetchone()
        return self._submission_from_db(row) if row else None

    def get_submission(
        self, *, course_id: str, assignment_id: str, submission_id: str
    ) -> Optional[SubmissionRow]:
        cur = self._execute(
            """
            SELECT id, assignment_id, course_id, user_sub, status, note,
                   created_at, updated_at, submitted_at
            FROM assignment_submissions
            WHERE course_id = %s AND assignment_id = %s AND id = %s
            """,
            (course_id, assignment_id, submission_id),
        )
        row = cur.fetchone()
        return self._submission_from_db(row) if row else None

    def list_submissions_for_assignment(
        self, *, course_id: str, assignment_id: str
    ) -> List[SubmissionRow]:
        cur = self._execute(
            """
            SELECT id, assignment_id, course_id, user_sub, status, note,
                   created_at, updated_at, submitted_at
            FROM assignment_submissions
            WHERE course_id = %s AND assignment_id = %s
            ORDER BY created_at ASC
            """,
            (course_id, assignment_id),
        )
        return [self._submission_from_db(r) for r in cur.fetchall()]

    def user_has_submission_for_course(self, *, course_id: str, user_sub: str) -> bool:
        cur = self._execute(
            """
            SELECT 1
            FROM assignment_submissions
            WHERE course_id = %s AND user_sub = %s
            LIMIT 1
            """,
            (course_id, user_sub),
        )
        return cur.fetchone() is not None

    def list_submissions_for_user(
        self, *, course_id: str, assignment_id: str, user_sub: str
    ) -> List[SubmissionRow]:
        cur = self._execute(
            """
            SELECT id, assignment_id, course_id, user_sub, status, note,
                   created_at, updated_at, submitted_at
            FROM assignment_submissions
            WHERE course_id = %s AND assignment_id = %s AND user_sub = %s
            ORDER BY created_at ASC
            """,
            (course_id, assignment_id, user_sub),
        )
        return [self._submission_from_db(r) for r in cur.fetchall()]

    def insert_submission(
        self,
        *,
        course_id: str,
        assignment_id: str,
        user_sub: str,
        status: str = "draft",
    ) -> SubmissionRow:
        conn = self._connection()

        def body() -> SubmissionRow:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO assignment_submissions (
                    course_id, assignment_id, user_sub, status
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (assignment_id, user_sub) WHERE status = 'draft'
                DO NOTHING
                RETURNING id, assignment_id, course_id, user_sub, status, note,
                          created_at, updated_at, submitted_at
                """,
                (course_id, assignment_id, user_sub, status),
            )
            row = cur.fetchone()
            if row is None:
                cur.execute(
                    _SUBMISSION_ROW_SELECT
                    + """
                    WHERE assignment_id = %s AND user_sub = %s AND status = 'draft'
                    """,
                    (assignment_id, user_sub),
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("insert_submission: draft row missing after conflict")
            return self._submission_from_db(row)

        return run_transaction(conn, body)

    def update_submission(self, row: SubmissionRow) -> SubmissionRow:
        conn = self._connection()

        def body() -> SubmissionRow:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE assignment_submissions SET
                    status = %s,
                    note = %s,
                    updated_at = NOW(),
                    submitted_at = %s
                WHERE id = %s
                RETURNING id, assignment_id, course_id, user_sub, status, note,
                          created_at, updated_at, submitted_at
                """,
                (row.status, row.note, row.submitted_at, row.id),
            )
            db_row = cur.fetchone()
            if db_row is None:
                raise RuntimeError("update_submission returned no row")
            return self._submission_from_db(db_row)

        return run_transaction(conn, body)

    def count_files_for_submission(self, submission_id: str) -> int:
        cur = self._execute(
            "SELECT COUNT(*) FROM assignment_submission_files WHERE submission_id = %s",
            (submission_id,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0

    def insert_submission_file(
        self,
        *,
        file_id: str,
        submission_id: str,
        assignment_id: str,
        course_id: str,
        title: str,
        file_type: str,
        object_key: str,
        content_type: str,
        byte_size: int,
        status: str = "pending",
    ) -> SubmissionFileRow:
        conn = self._connection()

        def body() -> SubmissionFileRow:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO assignment_submission_files (
                    id, submission_id, assignment_id, course_id, title, file_type,
                    object_key, content_type, byte_size, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, submission_id, assignment_id, course_id, title, file_type,
                          object_key, content_type, byte_size, status, created_at
                """,
                (
                    file_id,
                    submission_id,
                    assignment_id,
                    course_id,
                    title,
                    file_type,
                    object_key,
                    content_type,
                    byte_size,
                    status,
                ),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("insert_submission_file returned no row")
            return self._file_from_db(row)

        return run_transaction(conn, body)

    def get_submission_file(
        self, *, submission_id: str, file_id: str
    ) -> Optional[SubmissionFileRow]:
        cur = self._execute(
            """
            SELECT id, submission_id, assignment_id, course_id, title, file_type,
                   object_key, content_type, byte_size, status, created_at
            FROM assignment_submission_files
            WHERE submission_id = %s AND id = %s
            """,
            (submission_id, file_id),
        )
        row = cur.fetchone()
        return self._file_from_db(row) if row else None

    def mark_submission_file_ready(
        self, *, submission_id: str, file_id: str
    ) -> SubmissionFileRow:
        conn = self._connection()

        def body() -> SubmissionFileRow:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE assignment_submission_files
                SET status = 'ready'
                WHERE submission_id = %s AND id = %s
                RETURNING id, submission_id, assignment_id, course_id, title, file_type,
                          object_key, content_type, byte_size, status, created_at
                """,
                (submission_id, file_id),
            )
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("mark_submission_file_ready returned no row")
            return self._file_from_db(row)

        return run_transaction(conn, body)

    def insert_grade(
        self,
        *,
        submission_id: str,
        assignment_id: str,
        course_id: str,
        score_percent: int,
        pass_percent: int,
        passed: bool,
        feedback: str,
        graded_by: str,
        scores: Sequence[tuple[str, int]],
    ) -> GradeRow:
        conn = self._connection()

        def body() -> GradeRow:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT status FROM assignment_submissions
                WHERE id = %s
                FOR UPDATE
                """,
                (submission_id,),
            )
            locked = cur.fetchone()
            if locked is None:
                raise RuntimeError("insert_grade: submission not found")
            sub_status = locked[0]
            if sub_status == "graded":
                raise Conflict("Grade is immutable", code="grade_immutable")
            if sub_status != "submitted":
                raise Conflict(
                    "Submission is not awaiting grade", code="not_submitted"
                )
            cur.execute(
                """
                INSERT INTO assignment_grades (
                    submission_id, assignment_id, course_id,
                    score_percent, pass_percent, passed, feedback, graded_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, submission_id, assignment_id, course_id,
                          score_percent, pass_percent, passed, feedback,
                          graded_by, graded_at
                """,
                (
                    submission_id,
                    assignment_id,
                    course_id,
                    score_percent,
                    pass_percent,
                    passed,
                    feedback,
                    graded_by,
                ),
            )
            grow = cur.fetchone()
            if grow is None:
                raise RuntimeError("insert_grade returned no row")
            grade_id = grow[0]
            score_rows: list[GradeScoreRow] = []
            for cid, pts in scores:
                cur.execute(
                    """
                    INSERT INTO assignment_grade_scores (grade_id, criterion_id, points)
                    VALUES (%s, %s, %s)
                    """,
                    (grade_id, cid, pts),
                )
                score_rows.append(GradeScoreRow(criterion_id=cid, points=pts))
            cur.execute(
                """
                UPDATE assignment_submissions
                SET status = 'graded', updated_at = NOW()
                WHERE id = %s
                """,
                (submission_id,),
            )
            return self._grade_from_db(grow, tuple(score_rows))

        try:
            return run_transaction(conn, body)
        except Conflict:
            raise
        except Exception as exc:
            if psycopg2 is not None:
                from psycopg2 import errors as pg_errors

                if isinstance(exc, pg_errors.UniqueViolation):
                    raise Conflict("Grade is immutable", code="grade_immutable") from exc
            raise

    def get_grade_for_submission(self, submission_id: str) -> Optional[GradeRow]:
        return self._load_grade(submission_id)

    def latest_assignment_grade_passed_for_user(
        self, *, assignment_id: str, user_sub: str
    ) -> bool:
        """True when the student's latest submission has a grade row with passed=true."""
        cur = self._execute(
            """
            SELECT g.passed
            FROM assignment_submissions s
            INNER JOIN assignment_grades g ON g.submission_id = s.id
            WHERE s.assignment_id = %s AND s.user_sub = %s
            ORDER BY s.created_at DESC
            LIMIT 1
            """,
            (assignment_id, user_sub),
        )
        row = cur.fetchone()
        return bool(row and row[0])

    def _batched_delete(self, sql: str, params: tuple) -> int:
        return delete_in_batches(self._connection(), sql, params)

    def delete_assignment_grade_scores_for_user(self, user_sub: str) -> int:
        return self._batched_delete(_DELETE_ASSIGNMENT_GRADE_SCORES_FOR_USER_SQL, (user_sub,))

    def delete_assignment_grades_for_user(self, user_sub: str) -> int:
        return self._batched_delete(_DELETE_ASSIGNMENT_GRADES_FOR_USER_SQL, (user_sub,))

    def delete_assignment_submission_files_for_user(self, user_sub: str) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_USER_SQL, (user_sub,)
        )

    def delete_assignment_submissions_for_user(self, user_sub: str) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSIONS_FOR_USER_SQL, (user_sub,)
        )

    def delete_assignment_grade_scores_for_course(self, course_id: str) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_GRADE_SCORES_FOR_COURSE_SQL, (course_id,)
        )

    def delete_assignment_grades_for_course(self, course_id: str) -> int:
        return self._batched_delete(_DELETE_ASSIGNMENT_GRADES_FOR_COURSE_SQL, (course_id,))

    def delete_assignment_submission_files_for_course(self, course_id: str) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_COURSE_SQL, (course_id,)
        )

    def delete_assignment_submissions_for_course(self, course_id: str) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSIONS_FOR_COURSE_SQL, (course_id,)
        )

    def delete_assignment_grade_scores_for_module(
        self, course_id: str, module_id: str
    ) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_GRADE_SCORES_FOR_MODULE_SQL,
            (course_id, module_id),
        )

    def delete_assignment_grades_for_module(self, course_id: str, module_id: str) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_GRADES_FOR_MODULE_SQL, (course_id, module_id)
        )

    def delete_assignment_submission_files_for_module(
        self, course_id: str, module_id: str
    ) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSION_FILES_FOR_MODULE_SQL,
            (course_id, module_id),
        )

    def delete_assignment_submissions_for_module(
        self, course_id: str, module_id: str
    ) -> int:
        return self._batched_delete(
            _DELETE_ASSIGNMENT_SUBMISSIONS_FOR_MODULE_SQL,
            (course_id, module_id),
        )
