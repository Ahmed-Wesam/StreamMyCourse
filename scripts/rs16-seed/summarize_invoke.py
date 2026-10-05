"""Print a non-sensitive summary of an rds_query Lambda response.

Never prints SQL, user subs, or raw error text (Postgres errors can echo the statement).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ALLOWED = frozenset(
    {
        "teacher_count",
        "student_count",
        "title",
        "status",
        "price_amount_minor",
        "amount_minor",
        "credential_id",
        "product_type",
        "environment",
        "modules",
        "lessons",
        "progress_rows",
        "pending_lessons",
        "paid_bundles",
    }
)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: summarize_invoke.py <response.json> <count|mutate|rows>")
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    mode = sys.argv[2]
    if not payload.get("ok"):
        err = str(payload.get("error") or "")
        print("ok=false error_len=" + str(len(err)))
        raise SystemExit(2)
    if mode == "mutate":
        print("ok=true rowcount=" + str(payload.get("rowcount")))
        return
    rows = payload.get("rows") or []
    if mode == "count":
        if not rows:
            print("ok=true count=0")
            return
        parts = _int_parts(rows[0])
        print("ok=true " + " ".join(parts) if parts else "ok=true")
        return
    if mode != "rows":
        raise SystemExit("unknown mode")
    print("ok=true rows=" + str(len(rows)))
    for row in rows:
        if not isinstance(row, dict):
            continue
        parts = []
        for key in row:
            if key not in _ALLOWED:
                continue
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                continue
            parts.append(key + "=" + str(value))
        if parts:
            print(" ".join(parts))


def _int_parts(row: dict) -> list[str]:
    parts: list[str] = []
    for key, value in row.items():
        if key not in _ALLOWED:
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        parts.append(key + "=" + str(value))
    return parts


if __name__ == "__main__":
    main()
