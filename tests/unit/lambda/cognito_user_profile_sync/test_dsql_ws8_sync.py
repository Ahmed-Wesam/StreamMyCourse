"""DSQL-8 S1: sync OCC, session bump DSQL, packaging contracts."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_COGNITO_SRC = _ROOT / "infrastructure" / "lambda" / "cognito_user_profile_sync"
_DB_TX = _ROOT / "infrastructure" / "lambda" / "catalog" / "services" / "common" / "db_tx.py"


def _ensure_db_tx() -> None:
    if "db_tx" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location("db_tx", _DB_TX)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["db_tx"] = mod


if str(_COGNITO_SRC) not in sys.path:
    sys.path.insert(0, str(_COGNITO_SRC))
_ensure_db_tx()

import repo as cognito_repo  # noqa: E402
from session_sync import handle_pre_token_generation  # noqa: E402
from sync_config import SyncConfig  # noqa: E402


class _PgCommitError(Exception):
    def __init__(self, pgcode: str | None = None) -> None:
        super().__init__(pgcode or "err")
        self.pgcode = pgcode


@pytest.fixture(autouse=True)
def reset_cached_factory() -> Any:
    cognito_repo._cached_factory = None
    yield
    cognito_repo._cached_factory = None


def _conn_with_commit_retry() -> tuple[MagicMock, dict[str, int]]:
    commits: dict[str, int] = {"n": 0}

    def _commit() -> None:
        commits["n"] += 1
        if commits["n"] == 1:
            raise _PgCommitError("40001")

    conn = MagicMock(name="conn")
    conn.autocommit = True
    conn.commit = MagicMock(side_effect=_commit)
    conn.rollback = MagicMock()
    cur = MagicMock()
    cur.fetchone.return_value = ("row",)
    conn.cursor.return_value = cur
    return conn, commits


def test_upsert_user_profile_retries_once_on_40001() -> None:
    conn, commits = _conn_with_commit_retry()

    def factory() -> MagicMock:
        return conn

    cognito_repo.upsert_user_profile(
        factory, user_sub="u1", email="a@b.com", role="student"
    )

    assert commits["n"] == 2
    assert conn.commit.call_count == 2


def test_set_student_active_session_id_uses_run_transaction() -> None:
    conn, commits = _conn_with_commit_retry()

    cognito_repo.set_student_active_session_id(lambda: conn, user_sub="u1", session_id="s1")

    assert commits["n"] == 2
    assert conn.commit.call_count == 2
    sql = conn.cursor.return_value.execute.call_args.args[0]
    assert "student_active_session_id" in sql


def test_session_bump_allows_dsql_endpoint() -> None:
    cfg = SyncConfig(
        dsql_endpoint="cfuhjrrzy65ngud25rdqqso5t4.dsql.eu-west-1.on.aws",
        student_client_id="student-client",
        teacher_client_id="",
    )
    event = {
        "triggerSource": "TokenGeneration_Authentication",
        "callerContext": {"clientId": "student-client"},
        "request": {
            "userAttributes": {"sub": "sub-1", "email": "s@example.com"},
        },
        "response": {},
    }
    import session_sync as session_sync_mod

    with (
        patch.object(
            session_sync_mod,
            "get_cached_connection_factory",
            return_value=lambda: MagicMock(),
        ),
        patch.object(session_sync_mod, "set_student_active_session_id") as set_sess,
        patch.object(cognito_repo, "mirror_student_active_session_attribute") as mirror,
    ):
        out = handle_pre_token_generation(event, cfg)
    set_sess.assert_called_once()
    mirror.assert_not_called()
    assert out["response"]["claimsOverrideDetails"]["claimsToAddOrOverride"]["student_session_id"]


def test_sync_packaging_copies_db_tx() -> None:
    workflow = (_ROOT / ".github" / "workflows" / "deploy-backend.yml").read_text(encoding="utf-8")
    restore = (_ROOT / "scripts" / "restore-prod.sh").read_text(encoding="utf-8")
    assert "db_tx.py" in workflow
    assert "dsql_connect.py" in workflow
    assert "db_tx.py" in restore
    assert "dsql_connect.py" in restore
    assert "aurora-dsql-python-connector==0.2.7" in restore
