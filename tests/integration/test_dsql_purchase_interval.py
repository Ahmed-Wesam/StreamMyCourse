"""DSQL-5 S1: probe purchase-repo interval predicate on Aurora DSQL (D6).

When this test passes, D6 is **compatible**: keep
``NOW() AT TIME ZONE 'UTC'`` and ``INTERVAL '1 minute' * %s`` in
``purchases/repo.py`` unchanged.

Skipped unless ``DSQL_ENDPOINT`` is set or ``StreamMyCourse-Dsql-prod`` resolves.
"""

from __future__ import annotations

import pytest

from helpers.dsql_audit import admin_connect, execute_scalar, resolve_dsql_endpoint

_PROBE_SQL = (
    "SELECT ((NOW() AT TIME ZONE 'UTC') - (INTERVAL '1 minute' * %s)) IS NOT NULL"
)

pytestmark = pytest.mark.skipif(
    not resolve_dsql_endpoint(),
    reason="DSQL endpoint not configured (DSQL_ENDPOINT or StreamMyCourse-Dsql-prod)",
)


def test_dsql_purchase_interval_predicate_d6_compatible() -> None:
    """Live cluster probe for D6; green means do not change purchases/repo.py SQL."""
    with admin_connect() as conn:
        result = execute_scalar(conn, _PROBE_SQL, (30,))
    assert result is True, "D6 interval predicate must execute on DSQL cluster"
