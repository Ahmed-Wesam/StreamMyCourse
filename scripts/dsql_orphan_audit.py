#!/usr/bin/env python3
"""Report orphan rows for every FK in the DSQL schema (plans/dsql-ws1-foundation.md S7)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _REPO_ROOT / "scripts"
_CATALOG = _REPO_ROOT / "infrastructure" / "lambda" / "catalog"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(_CATALOG) not in sys.path:
    sys.path.insert(0, str(_CATALOG))

from dsql_connect import connect, connection_error  # noqa: E402

from dsql_fk_pairs import DSQL_FOREIGN_KEY_EDGES, ForeignKeyEdge, build_orphan_count_sql  # noqa: E402

DSQL_USER_ADMIN = "admin"


def fk_orphan_counts(conn: Any, *, edges: Sequence[ForeignKeyEdge] = DSQL_FOREIGN_KEY_EDGES) -> list[tuple[str, int]]:
    """Return ``(label, count)`` only for edges with a non-zero orphan count."""
    findings: list[tuple[str, int]] = []
    with conn.cursor() as cur:
        for edge in edges:
            sql = build_orphan_count_sql(edge)
            cur.execute(sql)
            row = cur.fetchone()
            count = int(row[0]) if row else 0
            if count:
                findings.append((edge.label, count))
    return findings


def run_audit(conn: Any) -> int:
    findings = fk_orphan_counts(conn)
    if not findings:
        print("dsql_orphan_audit: 0 findings")
        return 0
    for label, count in findings:
        print(f"orphan_fk {label} count={count}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="FK orphan audit for Aurora DSQL app schema")
    parser.add_argument(
        "--host",
        default=os.environ.get("DSQL_ENDPOINT", ""),
        help="Cluster endpoint hostname (DSQL_ENDPOINT)",
    )
    args = parser.parse_args()
    host = (args.host or "").strip()
    if not host:
        print("DSQL endpoint host required (DSQL_ENDPOINT or --host)", file=sys.stderr)
        return 2
    try:
        conn = connect(DSQL_USER_ADMIN, host)
    except Exception as exc:
        print(str(connection_error(host, exc)), file=sys.stderr)
        return 2
    try:
        return run_audit(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
