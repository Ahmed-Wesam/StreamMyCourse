"""DSQL-2 S1: tags codec, OCC profile writes, delete_user_row."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Sequence, Tuple

import pytest

from services.auth.learning_preferences import DEFAULT_RESEARCH_INTEREST_TAGS
from services.auth.rds_repo import UserProfileRdsRepository, _row_to_profile


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)
    rowcount: int = 0
    execute_calls: int = 0

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))
        self.execute_calls += 1
        if self.execute_calls == 1 and _ConflictErr.raise_on_first:
            err = _ConflictErr()
            err.pgcode = "40001"
            raise err

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)


class _ConflictErr(Exception):
    raise_on_first = False


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


def _profile_row(tags: Any = None) -> Tuple[Any, ...]:
    now = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    tags_val = tags if tags is not None else []
    return (
        "sub-1",
        "a@b.com",
        "student",
        "sub-1",
        now,
        now,
        "",
        "",
        "",
        "",
        "",
        "",
        None,
        None,
        True,
        True,
        True,
        tags_val,
        None,
    )


class TestTagsCodec:
    def test_constructor_rejects_tags_as_jsonb_kwarg(self) -> None:
        with pytest.raises(TypeError):
            UserProfileRdsRepository(lambda: FakeConn(), tags_as_jsonb=True)

    def test_preference_update_binds_json_text(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [_profile_row('["surgical_research"]')]
        repo = UserProfileRdsRepository(lambda: conn)
        repo.update_learning_preferences(
            user_sub="sub-1",
            autoplay_next=True,
            auto_mark_complete=True,
            progress_celebrations=True,
            research_interest_tags=["surgical_research"],
        )
        _, params = conn.cursor_obj.executions[-1]
        assert params[3] == json.dumps(["surgical_research"])
        assert "%s::jsonb" in conn.cursor_obj.executions[-1][0]

    def test_reset_binds_default_tags_json(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [_profile_row()]
        repo = UserProfileRdsRepository(lambda: conn)
        repo.reset_built_preferences(user_sub="sub-1")
        _, params = conn.cursor_obj.executions[-1]
        assert params[0] == json.dumps(list(DEFAULT_RESEARCH_INTEREST_TAGS))
        assert "%s::jsonb" in conn.cursor_obj.executions[-1][0]

    def test_row_to_profile_parses_json_string_and_list_tags(self) -> None:
        expected = ["systematic_reviews"]
        from_json = _row_to_profile(_profile_row('["systematic_reviews"]'))
        from_list = _row_to_profile(_profile_row(["systematic_reviews"]))
        assert from_json["researchInterestTags"] == expected
        assert from_list["researchInterestTags"] == expected


class TestOccProfileWrites:
    def test_put_profile_retries_on_40001(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [_profile_row()]
        _ConflictErr.raise_on_first = True
        try:
            repo = UserProfileRdsRepository(lambda: conn)
            result = repo.put_profile(user_sub="sub-1", email="a@b.com", role="student")
            assert result["email"] == "a@b.com"
            assert conn.cursor_obj.execute_calls == 2
            assert conn.committed == 1
        finally:
            _ConflictErr.raise_on_first = False

    def test_update_profile_fields_retries_on_40001(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rows_to_return = [_profile_row()]
        _ConflictErr.raise_on_first = True
        now = datetime(2026, 6, 1, tzinfo=timezone.utc)
        try:
            repo = UserProfileRdsRepository(lambda: conn)
            repo.update_profile_fields(
                user_sub="sub-1",
                given_name="A",
                family_name="B",
                country="Jordan",
                profession="Researcher",
                institution="",
                research_interests="",
                terms_accepted_at=now,
                privacy_accepted_at=now,
            )
            assert conn.cursor_obj.execute_calls == 2
        finally:
            _ConflictErr.raise_on_first = False


class TestDeleteUserRow:
    def test_delete_user_row_sql_and_rowcount(self) -> None:
        conn = FakeConn()
        conn.cursor_obj.rowcount = 1
        repo = UserProfileRdsRepository(lambda: conn)

        def set_rowcount(sql: str, params: Sequence[Any] = ()) -> None:
            conn.cursor_obj.executions.append((sql, tuple(params)))
            conn.cursor_obj.rowcount = 1

        conn.cursor_obj.execute = set_rowcount  # type: ignore[method-assign]
        conn.cursor_obj.rowcount = 1
        count = repo.delete_user_row("uuid-sub")
        assert count == 1
        sql, params = conn.cursor_obj.executions[-1]
        assert "DELETE FROM users WHERE user_sub = %s" in sql
        assert params == ("uuid-sub",)

    def test_delete_user_row_23503_not_retried(self) -> None:
        conn = FakeConn()
        repo = UserProfileRdsRepository(lambda: conn)
        calls = {"n": 0}

        def fail_fk(sql: str, params: Sequence[Any] = ()) -> None:
            calls["n"] += 1
            err = Exception("fk")
            err.pgcode = "23503"  # type: ignore[attr-defined]
            raise err

        conn.cursor_obj.execute = fail_fk  # type: ignore[method-assign]
        with pytest.raises(Exception, match="fk"):
            repo.delete_user_row("uuid-sub")
        assert calls["n"] == 1
