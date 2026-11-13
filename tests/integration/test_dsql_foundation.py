"""DSQL-1 foundation gate (plans/dsql-ws1-foundation.md §11).

Skipped unless ``INTEGRATION_API_STACK`` ends with ``Api-dsql`` so the prod
suite does not require DSQL connectivity.
"""

from __future__ import annotations

import os
import threading
import uuid
from typing import Any, List

import httpx
import pytest

from helpers.api import ApiClient
from helpers.dsql_audit import (
    admin_connect,
    admin_connection,
    execute_scalar,
    fk_orphan_counts,
    run_orphan_audit_script,
    run_transaction,
)
def _is_dsql_preview_stack() -> bool:
    stack = os.environ.get("INTEGRATION_API_STACK", "").strip()
    return stack.endswith("Api-dsql")


pytestmark = pytest.mark.skipif(
    not _is_dsql_preview_stack(),
    reason="DSQL foundation tests require INTEGRATION_API_STACK ending with Api-dsql",
)

_SCRATCH_DDL = """
CREATE TABLE IF NOT EXISTS app.dsql_foundation_occ_scratch (
    id UUID PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 0
);
"""


def test_admin_select_one_via_dsql_audit() -> None:
    with admin_connect() as conn:
        assert execute_scalar(conn, "SELECT 1") == 1


def test_get_courses_without_token(api: ApiClient) -> None:
    base = os.environ.get("INTEGRATION_API_BASE_URL", "").rstrip("/")
    with httpx.Client(base_url=base, timeout=30.0) as client:
        resp = client.get("/courses")
    assert resp.status_code == 200


def test_course_create_delete_cascades_default_module(api: ApiClient, course_factory) -> None:
    """Authenticated create/delete; SQL proves course + default module rows are gone (no S3)."""
    course = course_factory(label="dsql-foundation", description="dsql-foundation")
    course_id = course.course_id

    with admin_connect() as conn:
        mod_count = execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.course_modules WHERE course_id = %s",
            (course_id,),
        )
        assert int(mod_count) >= 1

    assert api.delete_course(course_id).status_code == 200

    with admin_connect() as conn:
        course_left = execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.courses WHERE id = %s",
            (course_id,),
        )
        module_left = execute_scalar(
            conn,
            "SELECT COUNT(*) FROM app.course_modules WHERE course_id = %s",
            (course_id,),
        )
        assert int(course_left) == 0
        assert int(module_left) == 0


class _PgOccConflict(Exception):
    def __init__(self) -> None:
        super().__init__("serialization_failure")
        self.pgcode = "40001"


def test_concurrent_run_transaction_retries_40001() -> None:
    """Two writers on one scratch row: one 40001, helper retry commits both bodies."""
    row_id = uuid.uuid4()
    bodies: List[str] = []
    sync = threading.Event()
    arrived = {"n": 0}
    arrive_lock = threading.Lock()
    inject = {"left": False}
    a_done = threading.Event()
    first_pass = {"a": True, "b": True}

    with admin_connect() as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(_SCRATCH_DDL)
            cur.execute(
                "INSERT INTO app.dsql_foundation_occ_scratch (id, version) VALUES (%s, 0)",
                (str(row_id),),
            )

    def worker(tag: str, connection: Any) -> None:
        def body() -> None:
            bodies.append(tag)
            if first_pass[tag]:
                first_pass[tag] = False
                with arrive_lock:
                    arrived["n"] += 1
                    if arrived["n"] == 2:
                        sync.set()
                assert sync.wait(timeout=5.0)
            if tag == "b" and not inject["left"]:
                inject["left"] = True
                raise _PgOccConflict()
            if tag == "b":
                assert a_done.wait(timeout=5.0)
            with connection.cursor() as cur:
                cur.execute(
                    "UPDATE app.dsql_foundation_occ_scratch SET version = version + 1 WHERE id = %s",
                    (str(row_id),),
                )
            if tag == "a":
                a_done.set()

        run_transaction(connection, body, sleep=lambda _s: None)

    conn_a = admin_connection()
    conn_b = admin_connection()
    try:
        t1 = threading.Thread(target=worker, args=("a", conn_a))
        t2 = threading.Thread(target=worker, args=("b", conn_b))
        t1.start()
        t2.start()
        t1.join(timeout=30.0)
        t2.join(timeout=30.0)
        assert not t1.is_alive() and not t2.is_alive()
    finally:
        for c in (conn_a, conn_b):
            try:
                c.close()
            except Exception:
                pass

    assert bodies.count("a") == 1
    assert bodies.count("b") == 2, f"expected b to retry after 40001, bodies={bodies}"

    with admin_connect() as conn:
        version = execute_scalar(
            conn,
            "SELECT version FROM app.dsql_foundation_occ_scratch WHERE id = %s",
            (str(row_id),),
        )
        assert int(version) == 2
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM app.dsql_foundation_occ_scratch WHERE id = %s",
                (str(row_id),),
            )


def test_orphan_audit_zero_findings() -> None:
    with admin_connect() as conn:
        assert fk_orphan_counts(conn) == []
    proc = run_orphan_audit_script()
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "0 findings" in proc.stdout
