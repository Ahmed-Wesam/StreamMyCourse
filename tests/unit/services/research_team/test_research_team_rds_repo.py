"""DSQL-7c: research team repo JSONB areas and OCC writes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, List, Optional, Sequence, Tuple

import pytest
from psycopg2 import errors as pg_errors

from services.common.errors import Conflict
from services.research_team.ports import ApplicationRow
from services.research_team.rds_repo import ResearchTeamRdsRepository, _areas_from_db


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    rowcount: int = 1

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)

    def fetchall(self) -> List[Tuple[Any, ...]]:
        return []


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0
    rolled_back: int = 0
    autocommit: bool = True

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        self.rolled_back += 1


class _UniqueViolationWithConstraint(pg_errors.UniqueViolation):
    def __init__(self, *, constraint_name: str, message: str = "duplicate") -> None:
        super().__init__(message)
        self._constraint_name = constraint_name

    @property
    def diag(self) -> SimpleNamespace:
        return SimpleNamespace(constraint_name=self._constraint_name)


def test_areas_from_db_parses_json_string() -> None:
    assert _areas_from_db('["systematic_reviews"]') == ("systematic_reviews",)


def test_areas_from_db_accepts_list() -> None:
    assert _areas_from_db(["Clinical Research"]) == ("Clinical Research",)


class TestResearchAreasBinding:
    def test_dsql_insert_uses_jsonb_cast(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [
            (
                "app-1",
                "sub-1",
                "submitted",
                False,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                "Ada",
                "a@b.com",
                "Jordan",
                "Uni",
                "Student",
                0,
                0,
                "Beginner",
                "None",
                '["Clinical Research"]',
                "x",
                "y",
                "5",
                datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        ]
        repo = ResearchTeamRdsRepository(lambda: conn, areas_as_jsonb=True)
        row = ApplicationRow(
            id="app-1",
            user_sub="sub-1",
            status="submitted",
            reapply_allowed=False,
            submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            full_name="Ada",
            email="a@b.com",
            country="Jordan",
            institution="Uni",
            position="Student",
            publication_count=0,
            project_count=0,
            stats_experience="Beginner",
            sys_review_experience="None",
            research_areas=("Clinical Research",),
            interests="x",
            motivation="y",
            weekly_hours="5",
            acknowledged_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        repo.insert_application(row)
        sql = conn.cursor_obj.executions[0][0]
        assert "%s::jsonb" in sql
        areas_param = next(
            p
            for p in conn.cursor_obj.executions[0][1]
            if isinstance(p, str) and p.startswith("[")
        )
        assert areas_param == json.dumps(["Clinical Research"])

    def test_rds_insert_binds_list_without_jsonb_cast(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [
            (
                "app-1",
                "sub-1",
                "submitted",
                False,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                "Ada",
                "a@b.com",
                "Jordan",
                "Uni",
                "Student",
                0,
                0,
                "Beginner",
                "None",
                ["Clinical Research"],
                "x",
                "y",
                "5",
                datetime(2026, 1, 1, tzinfo=timezone.utc),
            )
        ]
        repo = ResearchTeamRdsRepository(lambda: conn, areas_as_jsonb=False)
        row = ApplicationRow(
            id="app-1",
            user_sub="sub-1",
            status="submitted",
            reapply_allowed=False,
            submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            full_name="Ada",
            email="a@b.com",
            country="Jordan",
            institution="Uni",
            position="Student",
            publication_count=0,
            project_count=0,
            stats_experience="Beginner",
            sys_review_experience="None",
            research_areas=("Clinical Research",),
            interests="x",
            motivation="y",
            weekly_hours="5",
            acknowledged_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        repo.insert_application(row)
        sql = conn.cursor_obj.executions[0][0]
        assert "::jsonb" not in sql
        assert ["Clinical Research"] in conn.cursor_obj.executions[0][1]


class TestResearchTeamOcc:
    def test_insert_application_40001_then_23505_raises_conflict(self) -> None:
        conn = FakeConn()
        attempts = {"n": 0}
        original = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            original(sql, params)
            if "INSERT INTO research_team_applications" in sql:
                attempts["n"] += 1
                if attempts["n"] == 1:
                    err = Exception("serialization failure")
                    err.pgcode = "40001"  # type: ignore[attr-defined]
                    raise err
                raise _UniqueViolationWithConstraint(
                    constraint_name="research_team_applications_one_open"
                )

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]
        repo = ResearchTeamRdsRepository(lambda: conn)
        row = ApplicationRow(
            id="app-1",
            user_sub="sub-1",
            status="submitted",
            reapply_allowed=False,
            submitted_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            full_name="Ada",
            email="a@b.com",
            country="Jordan",
            institution="Uni",
            position="Student",
            publication_count=0,
            project_count=0,
            stats_experience="Beginner",
            sys_review_experience="None",
            research_areas=("Clinical Research",),
            interests="x",
            motivation="y",
            weekly_hours="5",
            acknowledged_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        with pytest.raises(Conflict) as exc:
            repo.insert_application(row)
        assert exc.value.code == "application_open"
        assert attempts["n"] == 2

    def test_set_reapply_allowed_retries_40001_once(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [
            (
                "app-1",
                "sub-1",
                "rejected",
                True,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                "Ada",
                "a@b.com",
                "Jordan",
                "Uni",
                "Student",
                0,
                0,
                "Beginner",
                "None",
                ["Clinical Research"],
                "x",
                "y",
                "5",
                datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            (
                "app-1",
                "sub-1",
                "rejected",
                True,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                "Ada",
                "a@b.com",
                "Jordan",
                "Uni",
                "Student",
                0,
                0,
                "Beginner",
                "None",
                ["Clinical Research"],
                "x",
                "y",
                "5",
                datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ]
        updates = {"n": 0}
        original = conn.cursor_obj.execute

        def execute(sql: str, params: Sequence[Any] = ()) -> None:
            original(sql, params)
            if "UPDATE research_team_applications" in sql:
                updates["n"] += 1
                if updates["n"] == 1:
                    err = Exception("serialization failure")
                    err.pgcode = "40001"  # type: ignore[attr-defined]
                    raise err

        conn.cursor_obj.execute = execute  # type: ignore[method-assign]
        repo = ResearchTeamRdsRepository(lambda: conn)
        repo.set_reapply_allowed("app-1", allowed=True)
        assert updates["n"] == 2
        assert conn.committed == 1
