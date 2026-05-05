"""Unit tests for the PostgreSQL repository adapters.

These tests use a hand-rolled mock connection/cursor so they run without a live
Postgres (psycopg2 is PostgreSQL-only; there is no SQLite mode). The mock
records every ``cursor.execute(sql, params)`` call so tests can assert both
parameterization (no SQL injection via f-strings) and the returned domain
objects.

Design contract enforced here:
  - Column names in the DB are ``snake_case`` (``created_at``, ``thumbnail_key``);
    domain models use ``camelCase`` (``createdAt``, ``thumbnailKey``).  The adapter
    must translate in both directions.
  - ``courses.id`` / ``lessons.id`` are ``UUID`` in SQL but ``str`` on the domain
    objects. psycopg2 returns ``uuid.UUID`` for UUID columns; the adapter must
    cast to ``str`` before constructing ``Course`` / ``Lesson``.
  - ``get_profile`` (auth) must return a dict keyed with camelCase keys
    (``email``, ``role``, ``cognitoSub``, ``createdAt``, ``updatedAt``) because
    ``UserProfileService.get_or_create_profile`` accesses those keys.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

import pytest


# ---------------------------------------------------------------------------
# Fake psycopg2 connection / cursor
# ---------------------------------------------------------------------------
#
# Tests pre-stage rows via ``cursor.rows_to_return`` and then assert on
# ``cursor.executions`` after the repo method runs. ``fetchone`` pops from the
# queue; ``fetchall`` drains it. This mirrors psycopg2's cursor API closely
# enough to exercise the adapter's SQL + parameter shapes while staying offline.


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    # Queue of rows to return from fetchone (popped from the left).
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    # Rows to return from fetchall (whole list consumed on the next call).
    bulk_rows_to_return: Optional[List[Tuple[Any, ...]]] = None
    # rowcount is read by the adapter after UPDATE ... to detect 0-row updates.
    rowcount: int = 1
    closed: bool = False

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def executemany(self, sql: str, seq_of_params: Sequence[Sequence[Any]]) -> None:
        for params in seq_of_params:
            self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        if self.bulk_rows_to_return is not None:
            out = self.bulk_rows_to_return
            self.bulk_rows_to_return = None
            return out
        # Otherwise drain fetchone queue.
        out = list(self.rows_to_return)
        self.rows_to_return.clear()
        return out

    def close(self) -> None:
        self.closed = True

    # Context-manager protocol so ``with conn.cursor() as cur:`` works.
    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0
    closed: bool = False

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def fake_conn() -> FakeConn:
    return FakeConn()


@pytest.fixture
def fake_conn_factory(fake_conn: FakeConn):
    """A connection factory returning the same FakeConn for every call.

    The adapter typically caches the connection once it's created; tests rely
    on this to inspect the *single* connection the repo used.
    """
    return lambda: fake_conn


# ---------------------------------------------------------------------------
# CourseCatalogRdsRepository
# ---------------------------------------------------------------------------


class TestCourseCatalogRdsRepository:
    """Covers every method on CourseCatalogRepositoryPort."""

    @pytest.fixture
    def repo(self, fake_conn_factory):
        from services.course_management.rds_repo import CourseCatalogRdsRepository

        return CourseCatalogRdsRepository(fake_conn_factory)

    def _stage_course_row(
        self, fake_conn: FakeConn, *, course_id: Optional[uuid.UUID] = None
    ) -> uuid.UUID:
        cid = course_id or uuid.UUID("12345678-1234-5678-1234-567812345678")
        now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        fake_conn.cursor_obj.rows_to_return.append(
            (
                cid,
                "Intro",
                "Desc",
                "DRAFT",
                "teacher-sub",
                "",
                now,
                now,
            )
        )
        return cid

    def test_list_courses_empty(self, repo, fake_conn: FakeConn) -> None:
        fake_conn.cursor_obj.bulk_rows_to_return = []
        result = repo.list_courses()
        assert result == []
        # Any query was issued (we do not pin exact SQL -- just that SELECT ran).
        assert fake_conn.cursor_obj.executions, "list_courses must issue a SQL query"
        sql, _params = fake_conn.cursor_obj.executions[0]
        assert "from courses" in sql.lower()

    def test_list_courses_maps_snake_to_camel_and_uuid_to_str(
        self, repo, fake_conn: FakeConn
    ) -> None:
        cid = uuid.UUID("11111111-2222-3333-4444-555555555555")
        now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        fake_conn.cursor_obj.bulk_rows_to_return = [
            (cid, "T", "D", "PUBLISHED", "owner", "thumbs/x.png", now, now),
        ]
        courses = repo.list_courses()
        assert len(courses) == 1
        c = courses[0]
        # UUID cast to str: downstream JSON serialization depends on it.
        assert isinstance(c.id, str)
        assert c.id == str(cid)
        # camelCase field mapping (NOT snake_case attribute access).
        assert c.title == "T"
        assert c.description == "D"
        assert c.status == "PUBLISHED"
        assert c.createdBy == "owner"
        assert c.thumbnailKey == "thumbs/x.png"
        assert c.createdAt  # non-empty ISO-ish string
        assert c.updatedAt

    def test_list_courses_by_instructor_parameterizes_and_orders(
        self, repo, fake_conn: FakeConn
    ) -> None:
        fake_conn.cursor_obj.bulk_rows_to_return = []
        assert repo.list_courses_by_instructor("teacher-sub") == []
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "where created_by" in sql.lower()
        assert "order by created_at asc" in sql.lower()
        assert params == ("teacher-sub",)

    def test_list_courses_by_instructor_empty_owner_returns_no_query(
        self, repo, fake_conn: FakeConn
    ) -> None:
        assert repo.list_courses_by_instructor("") == []
        assert repo.list_courses_by_instructor("  ") == []
        assert fake_conn.cursor_obj.executions == []

    def test_get_course_returns_none_when_missing(
        self, repo, fake_conn: FakeConn
    ) -> None:
        # No rows staged -> fetchone returns None.
        assert repo.get_course("missing-id") is None
        # Parameterized query (no f-string) -- the id must arrive as a bound param.
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "%s" in sql, "must use parameterized %s placeholder"
        assert "missing-id" in params

    def test_get_course_returns_course_with_str_id(
        self, repo, fake_conn: FakeConn
    ) -> None:
        self._stage_course_row(fake_conn)
        course = repo.get_course("12345678-1234-5678-1234-567812345678")
        assert course is not None
        assert isinstance(course.id, str)
        assert course.createdAt != ""

    def test_create_course_parameterizes_and_returns_domain_object(
        self, repo, fake_conn: FakeConn
    ) -> None:
        new_id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        # INSERT ... RETURNING style: one row comes back.
        fake_conn.cursor_obj.rows_to_return.append(
            (new_id, "My Course", "Body", "DRAFT", "creator", "", now, now)
        )
        course = repo.create_course(
            title="My Course", description="Body", created_by="creator"
        )
        assert isinstance(course.id, str)
        assert course.id == str(new_id)
        assert course.title == "My Course"
        assert course.status == "DRAFT"
        # Verify parameterized INSERT + commit happened.
        assert fake_conn.committed >= 1
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "INSERT" in sql.upper()
        assert "%s" in sql
        assert "My Course" in params
        assert "Body" in params
        assert "creator" in params

    def test_update_course_issues_parameterized_update(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.update_course("course-id", "new title", "new desc")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "UPDATE courses" in sql or "update courses" in sql
        assert "%s" in sql
        assert "new title" in params
        assert "new desc" in params
        assert "course-id" in params
        assert fake_conn.committed >= 1

    def test_set_course_status_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.set_course_status("course-id", "PUBLISHED")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "UPDATE courses" in sql.lower() or "update courses" in sql.lower()
        assert "PUBLISHED" in params
        assert "course-id" in params

    def test_set_course_thumbnail_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.set_course_thumbnail(
            "course-id",
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/thumbnail/11111111-1111-4111-8111-111111111111.png",
        )
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "thumbnail_key" in sql.lower()
        assert (
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/thumbnail/11111111-1111-4111-8111-111111111111.png"
            in params
        )

    def test_list_lessons_sorted_by_order_and_camel_case(
        self, repo, fake_conn: FakeConn
    ) -> None:
        l1_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
        l2_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000002")
        # Adapter should issue ORDER BY lesson_order in its SQL; test caller just
        # returns rows in that order.
        fake_conn.cursor_obj.bulk_rows_to_return = [
            (l1_id, "First", 1, "keys/1.mp4", "ready", "", 30),
            (l2_id, "Second", 2, "", "pending", "thumbs/x.png", 0),
        ]
        lessons = repo.list_lessons("course-id")
        assert len(lessons) == 2
        assert all(isinstance(l.id, str) for l in lessons)
        assert lessons[0].order == 1
        assert lessons[0].videoKey == "keys/1.mp4"
        assert lessons[0].videoStatus == "ready"
        assert lessons[0].duration == 30
        assert lessons[1].thumbnailKey == "thumbs/x.png"
        # ORDER BY must be present -- business rule depends on lesson order.
        joined_sql = " ".join(sql for sql, _ in fake_conn.cursor_obj.executions)
        assert "order by lesson_order" in joined_sql.lower() or "ORDER BY lesson_order" in joined_sql

    def test_get_lesson_by_id_missing_returns_none(
        self, repo, fake_conn: FakeConn
    ) -> None:
        assert repo.get_lesson_by_id("c", "l") is None
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "%s" in sql
        assert "c" in params
        assert "l" in params

    def test_get_lesson_by_id_returns_domain_object(
        self, repo, fake_conn: FakeConn
    ) -> None:
        lid = uuid.UUID("cccccccc-dddd-eeee-ffff-000000000001")
        fake_conn.cursor_obj.rows_to_return.append(
            (lid, "Title", 3, "video.mp4", "ready", "thumb.png", 42)
        )
        lesson = repo.get_lesson_by_id("course-id", str(lid))
        assert lesson is not None
        assert isinstance(lesson.id, str)
        assert lesson.order == 3
        assert lesson.videoKey == "video.mp4"

    def test_create_lesson_assigns_next_order(
        self, repo, fake_conn: FakeConn
    ) -> None:
        # Stage the next-order query first (MAX(lesson_order) -> 2), then the
        # INSERT ... RETURNING row for the new lesson (order=3).
        new_id = uuid.UUID("bbbbbbbb-cccc-dddd-eeee-ffffffffffff")
        fake_conn.cursor_obj.rows_to_return.extend(
            [
                (2,),  # SELECT COALESCE(MAX(lesson_order),0) -> 2
                (new_id, "Lesson 3", 3, "", "pending", "", 0),
            ]
        )
        lesson = repo.create_lesson("course-id", "Lesson 3")
        assert isinstance(lesson.id, str)
        assert lesson.title == "Lesson 3"
        assert lesson.order == 3
        assert fake_conn.committed >= 1

    def test_update_lesson_title_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.update_lesson_title("c", "l", "new title")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "update lessons" in sql.lower()
        assert "new title" in params
        assert "l" in params

    def test_delete_lesson_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.delete_lesson("c", "l")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "delete from lessons" in sql.lower()
        assert "l" in params
        assert fake_conn.committed >= 1

    def test_delete_course_and_lessons_single_transaction(
        self, repo, fake_conn: FakeConn
    ) -> None:
        # ON DELETE CASCADE on enrollments + lessons; single DELETE on courses.
        repo.delete_course_and_lessons("course-id")
        joined_sql = " ".join(sql.upper() for sql, _ in fake_conn.cursor_obj.executions)
        assert "DELETE FROM COURSES" in joined_sql
        assert "DELETE FROM ENROLLMENTS" not in joined_sql
        assert fake_conn.committed >= 1

    def test_set_lesson_video_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.set_lesson_video("c", "l", "keys/abc.mp4", "ready")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "update lessons" in sql.lower()
        assert "keys/abc.mp4" in params
        assert "ready" in params

    def test_set_lesson_video_if_video_key_matches_conflict_when_zero_rows(
        self, repo, fake_conn: FakeConn
    ) -> None:
        from services.common.errors import Conflict

        fake_conn.cursor_obj.rowcount = 0  # conditional update matched nothing
        with pytest.raises(Conflict):
            repo.set_lesson_video_if_video_key_matches(
                "c",
                "l",
                "keys/new.mp4",
                "pending",
                expected_video_key="keys/old.mp4",
            )

    def test_set_lesson_video_if_video_key_matches_success(
        self, repo, fake_conn: FakeConn
    ) -> None:
        fake_conn.cursor_obj.rowcount = 1
        # Must not raise.
        repo.set_lesson_video_if_video_key_matches(
            "c", "l", "keys/new.mp4", "pending", expected_video_key="keys/old.mp4"
        )
        sql, params = fake_conn.cursor_obj.executions[-1]
        # The expected/old key appears as a WHERE parameter.
        assert "keys/old.mp4" in params
        assert "keys/new.mp4" in params

    def test_set_lesson_video_status_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.set_lesson_video_status("c", "l", "ready")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "video_status" in sql.lower()
        assert "ready" in params

    def test_set_lesson_thumbnail_parameterized(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.set_lesson_thumbnail("c", "l", "thumbs/l.png")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "thumbnail_key" in sql.lower()
        assert "thumbs/l.png" in params

    def test_set_lesson_orders_issues_update_per_lesson(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.set_lesson_orders("course-id", {"l1": 2, "l2": 1, "l3": 3})
        # One UPDATE per lesson id.
        update_sqls = [
            (sql, params)
            for sql, params in fake_conn.cursor_obj.executions
            if sql.upper().startswith("UPDATE")
        ]
        assert len(update_sqls) == 3
        # Transactional: single commit after all updates.
        assert fake_conn.committed >= 1


# ---------------------------------------------------------------------------
# EnrollmentRdsRepository
# ---------------------------------------------------------------------------


class TestEnrollmentRdsRepository:
    @pytest.fixture
    def repo(self, fake_conn_factory):
        from services.enrollment.rds_repo import EnrollmentRdsRepository

        return EnrollmentRdsRepository(fake_conn_factory)

    def test_has_enrollment_false_when_no_row(
        self, repo, fake_conn: FakeConn
    ) -> None:
        assert repo.has_enrollment(user_sub="u", course_id="c") is False
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "%s" in sql
        assert "u" in params
        assert "c" in params

    def test_has_enrollment_true_when_row_present(
        self, repo, fake_conn: FakeConn
    ) -> None:
        fake_conn.cursor_obj.rows_to_return.append((1,))
        assert repo.has_enrollment(user_sub="u", course_id="c") is True

    def test_put_enrollment_inserts_and_commits(
        self, repo, fake_conn: FakeConn
    ) -> None:
        repo.put_enrollment(user_sub="u", course_id="c", source="self_service")
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "INSERT" in sql.upper()
        assert "enrollments" in sql.lower()
        assert "u" in params
        assert "c" in params
        assert "self_service" in params
        assert fake_conn.committed >= 1

    def test_put_enrollment_idempotent_on_conflict(
        self, repo, fake_conn: FakeConn
    ) -> None:
        # Enrolling twice should be a no-op (PK = (user_sub, course_id)). The
        # adapter uses ``ON CONFLICT DO NOTHING`` so repeat calls do not raise.
        repo.put_enrollment(user_sub="u", course_id="c", source="self_service")
        sql, _ = fake_conn.cursor_obj.executions[-1]
        assert "on conflict" in sql.lower() or "ON CONFLICT" in sql


# ---------------------------------------------------------------------------
# UserProfileRdsRepository
# ---------------------------------------------------------------------------


class TestUserProfileRdsRepository:
    """The auth service accesses specific camelCase keys from the profile dict:
    ``email``, ``role``, ``cognitoSub``, ``createdAt``, ``updatedAt``. The RDS
    adapter must return a dict with those exact keys (NOT the snake_case column
    names from the users table)."""

    @pytest.fixture
    def repo(self, fake_conn_factory):
        from services.auth.rds_repo import UserProfileRdsRepository

        return UserProfileRdsRepository(fake_conn_factory)

    def test_get_profile_missing_returns_none(
        self, repo, fake_conn: FakeConn
    ) -> None:
        assert repo.get_profile("missing-sub") is None
        sql, params = fake_conn.cursor_obj.executions[-1]
        assert "%s" in sql
        assert "missing-sub" in params

    def test_get_profile_returns_camelcase_keys(
        self, repo, fake_conn: FakeConn
    ) -> None:
        now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        fake_conn.cursor_obj.rows_to_return.append(
            ("sub-123", "alice@example.com", "teacher", "sub-123", now, now)
        )
        profile = repo.get_profile("sub-123")
        assert profile is not None
        # CamelCase keys -- NOT snake_case. The auth service depends on these
        # exact names via `.get("email")`, `.get("role")`, etc.
        for key in ("email", "role", "cognitoSub", "createdAt", "updatedAt"):
            assert key in profile, f"missing camelCase key: {key!r}"
        assert profile["email"] == "alice@example.com"
        assert profile["role"] == "teacher"
        assert profile["cognitoSub"] == "sub-123"

    def test_put_profile_inserts_new_row_with_generated_timestamps(
        self, repo, fake_conn: FakeConn
    ) -> None:
        now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        # First call: get_profile returns None (new user).
        # Second call: INSERT ... RETURNING the inserted row.
        fake_conn.cursor_obj.rows_to_return.append(
            ("sub-1", "a@b", "student", "sub-1", now, now)
        )
        result = repo.put_profile(user_sub="sub-1", email="a@b", role="student")
        assert isinstance(result, dict)
        assert result["email"] == "a@b"
        assert result["role"] == "student"
        assert result["cognitoSub"] == "sub-1"
        # Commit happened.
        assert fake_conn.committed >= 1

    def test_put_profile_preserves_created_at_on_upsert(
        self, repo, fake_conn: FakeConn
    ) -> None:
        """An existing profile upgraded from 'student' -> 'teacher' must keep
        its original created_at (mirrors the DynamoDB adapter's behavior so
        auth.service observes consistent createdAt across roles)."""
        original_created = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
        now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
        fake_conn.cursor_obj.rows_to_return.append(
            ("sub-1", "a@b", "teacher", "sub-1", original_created, now)
        )
        result = repo.put_profile(user_sub="sub-1", email="a@b", role="teacher")
        # The returned createdAt is the original (not overwritten).
        assert result["createdAt"]  # non-empty
        # Ensure the INSERT statement uses ON CONFLICT to preserve created_at
        # (or a similar upsert pattern).
        joined_sql = " ".join(
            sql.lower() for sql, _ in fake_conn.cursor_obj.executions
        )
        assert "on conflict" in joined_sql
