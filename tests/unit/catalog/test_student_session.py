"""Slice 1: student session compare rules and RDS active-session lookup."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pytest

from services.auth.rds_repo import UserProfileRdsRepository
from services.auth.session import SESSION_SUPERSEDED, evaluate_student_session

STUDENT_CLIENT_ID = "student-client-id-example"
TEACHER_CLIENT_ID = "teacher-client-id-example"
ACTIVE_SESSION = "22222222-2222-2222-2222-222222222222"
OTHER_SESSION = "11111111-1111-1111-1111-111111111111"


def _claims(
    *,
    aud: str = STUDENT_CLIENT_ID,
    student_session_id: Optional[str] = None,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {"aud": aud}
    if student_session_id is not None:
        out["student_session_id"] = student_session_id
    return out


class TestEvaluateStudentSession:
    def test_rds_active_empty_allows_any_claim(self) -> None:
        assert (
            evaluate_student_session(
                _claims(student_session_id=OTHER_SESSION),
                active_session_id="",
                student_client_id=STUDENT_CLIENT_ID,
            )
            is None
        )

    def test_rds_active_empty_allows_missing_claim(self) -> None:
        assert (
            evaluate_student_session(
                _claims(),
                active_session_id="",
                student_client_id=STUDENT_CLIENT_ID,
            )
            is None
        )

    def test_rds_active_nonempty_matching_claim_allows(self) -> None:
        assert (
            evaluate_student_session(
                _claims(student_session_id=ACTIVE_SESSION),
                active_session_id=ACTIVE_SESSION,
                student_client_id=STUDENT_CLIENT_ID,
            )
            is None
        )

    def test_rds_active_nonempty_matching_custom_claim_allows(self) -> None:
        claims = {"aud": STUDENT_CLIENT_ID, "custom:student_session_id": ACTIVE_SESSION}
        assert (
            evaluate_student_session(
                claims,
                active_session_id=ACTIVE_SESSION,
                student_client_id=STUDENT_CLIENT_ID,
            )
            is None
        )

    @pytest.mark.parametrize(
        "presented",
        [
            OTHER_SESSION,
            None,
            "",
        ],
    )
    def test_rds_active_nonempty_mismatch_or_missing_claim_rejects(
        self, presented: str | None
    ) -> None:
        claims = _claims()
        if presented is not None:
            claims["student_session_id"] = presented

        assert (
            evaluate_student_session(
                claims,
                active_session_id=ACTIVE_SESSION,
                student_client_id=STUDENT_CLIENT_ID,
            )
            == SESSION_SUPERSEDED
        )

    def test_teacher_aud_is_noop_allow_even_when_sessions_mismatch(self) -> None:
        assert (
            evaluate_student_session(
                _claims(
                    aud=TEACHER_CLIENT_ID,
                    student_session_id=OTHER_SESSION,
                ),
                active_session_id=ACTIVE_SESSION,
                student_client_id=STUDENT_CLIENT_ID,
            )
            is None
        )


@dataclass
class _FakeCursor:
    executions: List[Tuple[str, Tuple[Any, ...]]] = field(default_factory=list)
    rows_to_return: List[Tuple[Any, ...]] = field(default_factory=list)

    def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.executions.append((sql, tuple(params)))

    def fetchone(self) -> Optional[Tuple[Any, ...]]:
        if not self.rows_to_return:
            return None
        return self.rows_to_return.pop(0)


@dataclass
class _FakeConn:
    cursor_obj: _FakeCursor = field(default_factory=_FakeCursor)

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class TestUserProfileRdsRepositoryGetStudentActiveSession:
    def test_get_student_active_session_id_queries_users_table(self) -> None:
        conn = _FakeConn()
        conn.cursor_obj.rows_to_return = [(ACTIVE_SESSION,)]
        repo = UserProfileRdsRepository(lambda: conn)

        assert repo.get_student_active_session_id("user-sub-1") == ACTIVE_SESSION

        sql, params = conn.cursor_obj.executions[0]
        assert "student_active_session_id" in sql
        assert "users" in sql
        assert params == ("user-sub-1",)

    def test_get_student_active_session_id_returns_empty_when_user_missing(self) -> None:
        conn = _FakeConn()
        repo = UserProfileRdsRepository(lambda: conn)

        assert repo.get_student_active_session_id("missing-sub") == ""
