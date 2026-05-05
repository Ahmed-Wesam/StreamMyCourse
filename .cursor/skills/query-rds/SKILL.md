---
name: query-rds
description: >-
  Runs SQL against StreamMyCourse RDS via the in-VPC RdsQuery Lambda using the
  operator runbook. Use when the user invokes /query_rds, asks to query RDS,
  run read-only SQL, gated mutating SQL, or catalog wipe against Postgres behind
  StreamMyCourse-RdsQuery-<env>.
disable-model-invocation: true
---

# /query_rds

## Canonical procedure

1. **Read the runbook first** (every time): `infrastructure/database/RDS_QUERY_RUNBOOK.md` at the repository root (use the Read tool on that path).
2. **Follow it exactly** for deploy, payload shape, `aws lambda invoke`, security gates (`confirm`, `allow_mutating_sql`, `wipe_catalog`, env flags), and any legacy maintenance sections only when the user’s task matches that scenario.

The runbook is the source of truth; this skill does not replace it.

## Agent execution notes

- **No HTTP API:** use `aws lambda invoke` on `StreamMyCourse-RdsQuery-<env>` only, with credentials that have `lambda:InvokeFunction` on that function (see runbook IAM section).
- **Region:** default `eu-west-1` unless stacks or user specify otherwise.
- **Payload file:** keep JSON in a file (PowerShell-safe); use `--cli-binary-format raw-in-base64-out` and `--payload fileb://...` as in the runbook.
- **Output file:** on Windows, use a path under `%TEMP%` / `$env:TEMP` instead of `/tmp/...` when adapting runbook examples.
- **Read vs mutating vs wipe:** obey runbook exclusivity and env flags; do not suggest bypassing gates. For **read** queries, use the read payload pattern; use mutating or wipe paths only when the user explicitly needs them **and** runbook prerequisites are met.
- **Discovery:** for account-specific values, use **`.cursor/skills/aws-cli/SKILL.md`** and **`.cursor/skills/use-cli/SKILL.md`** instead of guessing ARNs or regions.

## User intent

- If the user names a **SQL string** and **environment** (`dev` / `prod`), construct the appropriate `payload.json`, invoke as documented, show the Lambda response body, and call out errors or guard rejections plainly.
- If they only say “query RDS” without SQL, ask once for **environment** and **statement** (or confirm read-only vs mutating and get explicit approval for mutating/wipe paths).
