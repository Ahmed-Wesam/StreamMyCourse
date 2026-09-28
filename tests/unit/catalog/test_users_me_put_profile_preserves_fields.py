"""RS-6 Slice A: put_profile upsert must not wipe extended profile columns."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Sequence, Tuple

import pytest

from dataclasses import dataclass, field
from typing import List, Optional

from services.auth.rds_repo import UserProfileRdsRepository


@dataclass
class FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)


@dataclass
class FakeConn:
    cursor_obj: FakeCursor = field(default_factory=FakeCursor)
    committed: int = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.committed += 1

    def rollback(self) -> None:
        pass


def _profile_row(
    *,
    given_name: str = "Ada",
    country: str = "Jordan",
) -> Tuple[Any, ...]:
    now = datetime(2026, 5, 3, 12, 0, 0, tzinfo=timezone.utc)
    return (
        "sub-1",
        "a@b.com",
        "student",
        "sub-1",
        now,
        now,
        given_name,
        "Lovelace",
        country,
        "Researcher",
        "Inst",
        "Stats",
        now,
        now,
    )


class TestPutProfilePreservesProfileColumns:
    @pytest.fixture
    def repo(self) -> UserProfileRdsRepository:
        return UserProfileRdsRepository(lambda: FakeConn())

    def test_put_profile_on_conflict_does_not_update_profile_columns(
        self, repo: UserProfileRdsRepository
    ) -> None:
        fake_conn = FakeConn()
        repo = UserProfileRdsRepository(lambda: fake_conn)
        fake_conn.cursor_obj.rows_to_return.append(_profile_row())

        repo.put_profile(user_sub="sub-1", email="new@example.com", role="teacher")

        conflict_sql = " ".join(
            sql.lower() for sql, _ in fake_conn.cursor_obj.executions
        )
        assert "on conflict" in conflict_sql
        do_update = conflict_sql.split("do update", 1)[1].split("returning")[0]
        assert "given_name" not in do_update
        assert "country" not in do_update
