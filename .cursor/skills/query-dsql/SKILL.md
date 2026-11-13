---
name: query-dsql
description: >-
  Runs SQL against Aurora DSQL for StreamMyCourse using the operator runbook.
  Use when the user invokes /query_dsql, asks to query DSQL, run orphan audit,
  check preview schema, or connect admin to StreamMyCourse-Dsql-prod.
disable-model-invocation: true
---

# /query_dsql

## Canonical procedure

1. **Read the runbook first** (every time): `infrastructure/docs/dsql-query-runbook.md` (Read tool on that path).
2. **Follow it** for endpoint discovery, `aws dsql generate-db-connect-admin-auth-token`, database `postgres`, `sslmode=require`, and `SET search_path TO app`.
3. For FK integrity checks, run `python scripts/dsql_orphan_audit.py` with `DSQL_ENDPOINT` set (exit 0 = no orphans).

The runbook is the source of truth; this skill does not replace it.

## Agent execution notes

- **Region:** default `eu-west-1`. Cluster stack: `StreamMyCourse-Dsql-prod`.
- **Admin only** for ad-hoc SQL from the operator machine or CI applier jobs. App runtime uses `smc_app` via `dsql:DbConnect`.
- **psql 14+** required for SNI. Mention this when connection fails with opaque TLS errors.
- **Never log** IAM DB auth tokens, passwords, or full DSNs. Hostname and token **length** are fine.
- **Discovery:** use `.cursor/skills/aws-cli/SKILL.md` for stack outputs instead of guessing hostnames.
- **Preview gate:** integration SQL lives in `tests/integration/test_dsql_foundation.py`; it is skipped unless `INTEGRATION_API_STACK` ends with `Api-dsql`.

## User intent

- If the user names **SQL** and wants DSQL: mint admin token per runbook, connect with `search_path=app`, run the statement, summarize results without secrets.
- If they ask for **orphan / FK audit**: run `scripts/dsql_orphan_audit.py` or call `fk_orphan_counts` via `tests/integration/helpers/dsql_audit.py` in test contexts.
- If they only say “query DSQL”, ask once for **read vs write** intent and confirm `DSQL_ENDPOINT` or deploy stack availability.
