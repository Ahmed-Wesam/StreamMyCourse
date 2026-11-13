"""DSQL-7a S1: probe assignment-related SELECT shapes on Aurora DSQL (D7).

When these tests pass, ``user_sub = ANY(%s)`` with a Python text list is compatible.
"""

from __future__ import annotations

import pytest

from helpers.dsql_audit import admin_connect, execute_scalar, resolve_dsql_endpoint

_ANY_TEXT_SQL = """
            SELECT COUNT(*)::int
            FROM users
            WHERE user_sub = ANY(%s)
            """

_PROBE_SUB = "probe-dsql-7-not-a-user"

pytestmark = pytest.mark.skipif(
    not resolve_dsql_endpoint(),
    reason="DSQL endpoint not configured (DSQL_ENDPOINT or StreamMyCourse-Dsql-prod)",
)


def test_dsql_any_text_list_empty_d7() -> None:
    with admin_connect() as conn:
        count = execute_scalar(conn, _ANY_TEXT_SQL, ([],))
    assert count == 0


def test_dsql_any_text_list_one_element_d7() -> None:
    with admin_connect() as conn:
        count = execute_scalar(conn, _ANY_TEXT_SQL, ([_PROBE_SUB],))
    assert count == 0
