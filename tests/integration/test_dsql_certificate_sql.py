"""DSQL-7b S1: certificate credential lookup indexes on Aurora DSQL."""

from __future__ import annotations

import pytest

from helpers.dsql_audit import admin_connect, execute_scalar, resolve_dsql_endpoint

pytestmark = pytest.mark.skipif(
    not resolve_dsql_endpoint(),
    reason="DSQL endpoint not configured (DSQL_ENDPOINT or StreamMyCourse-Dsql-prod)",
)

_COURSE_CRED = "RS-ABCDEF-2026-0123456789"
_BUNDLE_CRED = "RS-B00001-2026-0123456789"


def _explain_contains(conn, sql: str, params: tuple) -> str:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return str(row[0] if row else "")


def test_explain_course_credential_uses_upper_index() -> None:
    with admin_connect() as conn:
        plan = _explain_contains(
            conn,
            """
            EXPLAIN SELECT id FROM app.certificates
            WHERE upper(credential_id) = upper(%s)
            """,
            (_COURSE_CRED,),
        )
    lowered = plan.lower()
    assert "certificates_credential_id_upper" in lowered


def test_explain_bundle_credential_uses_upper_index() -> None:
    with admin_connect() as conn:
        plan = _explain_contains(
            conn,
            """
            EXPLAIN SELECT id FROM app.bundle_certificates
            WHERE upper(credential_id) = upper(%s)
            """,
            (_BUNDLE_CRED,),
        )
    lowered = plan.lower()
    assert "bundle_certificates_credential_id_upper" in lowered


def test_schema_migration_0004_applied() -> None:
    with admin_connect() as conn:
        version = execute_scalar(
            conn,
            "SELECT version FROM app.schema_migrations WHERE version = %s",
            ("0004",),
        )
    assert version == "0004"
