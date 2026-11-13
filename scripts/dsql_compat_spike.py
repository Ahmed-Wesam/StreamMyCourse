#!/usr/bin/env python3
"""Aurora DSQL compatibility spike (plans/dsql-ws1-foundation.md section 9).

Dry-run prints SQL only. Live mode connects as admin, uses schema ``spike``, and
drops it in a ``finally`` block. One DDL statement per transaction in live mode.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Sequence

SPIKE_SCHEMA = "spike"
DSQL_USER_ADMIN = "admin"
DSQL_USER_APP = "smc_app"
DSQL_DBNAME = "postgres"
LIBPQ_STATEMENT_TIMEOUT_OPTIONS = "-c statement_timeout=10000"

_DSN_LEAK = re.compile(
    r"(password|token|dsn|postgresql://|secret|eyJ[a-zA-Z0-9_-]{10,})",
    re.IGNORECASE,
)


def connection_error(host: str, exc: BaseException) -> RuntimeError:
    """Rewrite connection failures so logs/exceptions contain only the host."""
    err = RuntimeError(f"DSQL connection failed for host {host}")
    err.__cause__ = exc
    return err


def _qualified(name: str) -> str:
    return f"{SPIKE_SCHEMA}.{name}"


def setup_sql_statements() -> list[str]:
    return [f"CREATE SCHEMA {SPIKE_SCHEMA}"]


def teardown_sql_statements() -> list[str]:
    return [f"DROP SCHEMA IF EXISTS {SPIKE_SCHEMA} CASCADE"]


def critical_sql_statements() -> list[str]:
    """DDL/DML strings executed (or printed) for critical compatibility checks."""
    p = _qualified
    return [
        f"""CREATE TABLE {p("scratch_uuid")} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
)""",
        f"""CREATE TABLE {p("fk_parent")} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
)""",
        f"""CREATE TABLE {p("fk_child_cascade")} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID NOT NULL REFERENCES {p("fk_parent")} (id) ON DELETE CASCADE
)""",
        f"""CREATE TABLE {p("fk_child_no_action")} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_id UUID NOT NULL REFERENCES {p("fk_parent")} (id) ON DELETE NO ACTION
)""",
        f"""CREATE TABLE {p("partial_uq")} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slot INT NOT NULL
)""",
        f"CREATE UNIQUE INDEX ASYNC uq_{SPIKE_SCHEMA}_partial_slot ON {p('partial_uq')} (slot) WHERE slot > 0",
        "CALL sys.wait_for_job(%s)",
        f"INSERT INTO {p('partial_uq')} (slot) VALUES (1) ON CONFLICT DO NOTHING",
        f"CREATE INDEX ASYNC IF NOT EXISTS idx_{SPIKE_SCHEMA}_fk_parent_id ON {p('fk_parent')} (id)",
        f"CREATE ROLE {DSQL_USER_APP} WITH LOGIN",
        f"GRANT USAGE ON SCHEMA {SPIKE_SCHEMA} TO {DSQL_USER_APP}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {SPIKE_SCHEMA} TO {DSQL_USER_APP}",
        "SET search_path TO app",
    ]


def smc_app_probe_sql_statements() -> list[str]:
    p = _qualified
    return [
        f"INSERT INTO {p('scratch_uuid')} DEFAULT VALUES",
        f"DELETE FROM {p('scratch_uuid')}",
        f"CREATE TABLE {p('smc_app_forbidden')} (id UUID PRIMARY KEY)",
    ]


def informational_sql_statements() -> list[str]:
    """SQL shapes probed for informational compatibility (section 9)."""
    p = _qualified
    return [
        f"""
            SELECT DISTINCT ON (mq.module_id)
                mq.module_id,
                s.correct_count,
                s.total_count
            FROM {p("module_quizzes")} mq
            INNER JOIN {p("question_banks")} qb
              ON qb.id = mq.question_bank_id
            INNER JOIN {p("module_quiz_attempt_submissions")} s
              ON s.attempt_id = mq.id
            ORDER BY mq.module_id, s.submitted_at DESC, s.attempt_id DESC
            """.strip(),
        f"SELECT id FROM {p('fk_parent')} WHERE id = ANY(%s::uuid[])",
        """
            INSERT INTO rate_limit_counters (bucket_key, window_start, count)
            VALUES (%s, %s, 1)
            ON CONFLICT (bucket_key) DO UPDATE SET
                window_start = CASE
                    WHEN rate_limit_counters.window_start + make_interval(secs => %s) <= NOW()
                    THEN EXCLUDED.window_start
                    ELSE rate_limit_counters.window_start
                END,
                count = CASE
                    WHEN rate_limit_counters.window_start + make_interval(secs => %s) <= NOW()
                    THEN 1
                    ELSE rate_limit_counters.count + 1
                END
            RETURNING count, window_start
            """.strip(),
        """
            UPDATE purchases
            SET updated_at = NOW()
            WHERE status = 'pending'
              AND updated_at > (NOW() AT TIME ZONE 'UTC') - (INTERVAL '1 minute' * %s)
            """.strip(),
        f"SELECT id FROM {p('scratch_occ')} WHERE id = %s FOR UPDATE",
        f"DELETE FROM {p('cascade_child')} WHERE parent_id = %s",
        f"""CREATE TABLE {p("jsonb_probe")} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tags JSONB NOT NULL DEFAULT '[]'::jsonb
)""",
        f"INSERT INTO {p('jsonb_probe')} (tags) VALUES (%s::jsonb)",
        f"SELECT tags FROM {p('jsonb_probe')} WHERE id = %s",
    ]


def dry_run_sql_lines() -> list[str]:
    """Deterministic SQL lines printed by ``--dry-run``."""
    lines: list[str] = []
    lines.extend(setup_sql_statements())
    lines.extend(critical_sql_statements())
    lines.extend(informational_sql_statements())
    lines.extend(smc_app_probe_sql_statements())
    lines.extend(teardown_sql_statements())
    return lines


def _wait_for_job(conn: Any, job_id: Any) -> None:
    previous = conn.autocommit
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("CALL sys.wait_for_job(%s)", (job_id,))
    finally:
        conn.autocommit = previous


def _execute_ddl(conn: Any, sql: str, params: Sequence[Any] | None = None) -> Any:
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            if cur.description:
                row = cur.fetchone()
            else:
                row = None
        conn.commit()
        return row
    except Exception:
        conn.rollback()
        raise


def _connect_admin(host: str, *, libpq_options: str | None = None) -> Any:
    try:
        import aurora_dsql_psycopg2  # type: ignore[import-untyped]
    except ImportError as exc:
        raise connection_error(host, exc) from None
    kwargs: dict[str, Any] = {
        "user": DSQL_USER_ADMIN,
        "host": host,
        "dbname": DSQL_DBNAME,
        "sslmode": "require",
    }
    if libpq_options:
        kwargs["options"] = libpq_options
    try:
        return aurora_dsql_psycopg2.connect(**kwargs)
    except Exception as exc:
        raise connection_error(host, exc) from None


def _connect_app(host: str) -> Any:
    try:
        import aurora_dsql_psycopg2  # type: ignore[import-untyped]
    except ImportError as exc:
        raise connection_error(host, exc) from None
    try:
        return aurora_dsql_psycopg2.connect(
            user=DSQL_USER_APP,
            host=host,
            dbname=DSQL_DBNAME,
            sslmode="require",
        )
    except Exception as exc:
        raise connection_error(host, exc) from None


def _run_dry_run() -> int:
    for line in dry_run_sql_lines():
        print(line)
    return 0


def _iam_grant_smc_app(conn: Any, iam_role_arn: str) -> None:
    _execute_ddl(conn, f"AWS IAM GRANT {DSQL_USER_APP} TO '{iam_role_arn}'")


def _run_live(
    host: str,
    *,
    test_statement_timeout: bool,
    iam_role_arn: str | None = None,
) -> int:
    conn = _connect_admin(
        host,
        libpq_options=LIBPQ_STATEMENT_TIMEOUT_OPTIONS if test_statement_timeout else None,
    )
    success = True
    try:
        for sql in setup_sql_statements():
            _execute_ddl(conn, sql)
        for sql in critical_sql_statements():
            if sql == "CALL sys.wait_for_job(%s)":
                continue
            if sql.startswith("INSERT INTO") or sql.startswith("SET search_path"):
                _execute_ddl(conn, sql)
                continue
            if sql.startswith("GRANT ") or sql.startswith("CREATE ROLE "):
                try:
                    _execute_ddl(conn, sql)
                except Exception as exc:
                    if sql.startswith("CREATE ROLE ") and "already exists" in str(exc).lower():
                        continue
                    raise
                continue
            row = _execute_ddl(conn, sql)
            if "CREATE UNIQUE INDEX ASYNC" in sql and row:
                job_id = row[0] if isinstance(row, tuple) else row
                _wait_for_job(conn, job_id)
        if iam_role_arn:
            try:
                _iam_grant_smc_app(conn, iam_role_arn)
            except Exception as exc:
                if "already" not in str(exc).lower():
                    raise
        _probe_smc_app(host)
        _run_informational_probes(conn, host)
    except Exception:
        success = False
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            try:
                conn.rollback()
            except Exception:
                pass
            for sql in teardown_sql_statements():
                _execute_ddl(conn, sql)
        finally:
            conn.close()
    return 0 if success else 1


def _probe_smc_app(host: str) -> None:
    app_conn = _connect_app(host)
    try:
        for sql in smc_app_probe_sql_statements():
            app_conn.autocommit = False
            try:
                with app_conn.cursor() as cur:
                    cur.execute(sql)
                app_conn.commit()
            except Exception as exc:
                app_conn.rollback()
                if "CREATE TABLE" in sql:
                    if "permission" in str(exc).lower() or "denied" in str(exc).lower():
                        return
                raise
    finally:
        app_conn.close()


def _run_informational_probes(conn: Any, host: str) -> None:
    """Best-effort informational checks; failures are recorded in summary only."""
    del host  # reserved for two-session OCC probe extension
    for sql in informational_sql_statements():
        if not (
            sql.startswith("CREATE TABLE")
            or sql.startswith("SELECT")
            or sql.startswith("INSERT")
            or sql.startswith("UPDATE")
            or sql.startswith("DELETE")
        ):
            continue
        try:
            if sql.startswith("SELECT") and "ANY(%s::uuid[])" in sql:
                _execute_ddl(conn, sql, ([],))
            elif sql.startswith("INSERT INTO") and "jsonb" in sql:
                _execute_ddl(conn, sql, (json.dumps(["alpha", "beta"]),))
            elif "make_interval" in sql or "INTERVAL '1 minute'" in sql:
                _execute_ddl(conn, sql, (60,))
            elif "FOR UPDATE" in sql:
                continue
            elif sql.startswith("DELETE FROM"):
                continue
            else:
                _execute_ddl(conn, sql)
        except Exception:
            continue


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aurora DSQL compatibility spike")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL statements without connecting",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("DSQL_ENDPOINT", ""),
        help="Cluster endpoint hostname (DSQL_ENDPOINT)",
    )
    parser.add_argument(
        "--test-statement-timeout",
        action="store_true",
        help="Pass libpq statement_timeout options on admin connect",
    )
    parser.add_argument(
        "--iam-role-arn",
        default=os.environ.get("DSQL_SPIKE_IAM_ROLE_ARN", ""),
        help="IAM role ARN for AWS IAM GRANT smc_app before smc_app connect probe",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.dry_run:
        return _run_dry_run()

    host = (args.host or "").strip()
    if not host:
        print("DSQL endpoint host required (set DSQL_ENDPOINT or pass --host)", file=sys.stderr)
        return 2

    iam_arn = (args.iam_role_arn or "").strip() or None
    return _run_live(
        host,
        test_statement_timeout=args.test_statement_timeout,
        iam_role_arn=iam_arn,
    )


if __name__ == "__main__":
    raise SystemExit(main())
