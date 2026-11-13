# ADR 0016 — RDS PostgreSQL → Aurora DSQL (cost-driven, pre-launch)

## Status

Proposed

## Context

StreamMyCourse is **pre-launch** (no customers). The catalog, rate limits, purchases, and analytics already live on **RDS PostgreSQL** inside a private VPC with interface/gateway endpoints (see [ADR-0008](./adr-0008-dynamodb-to-rds-migration.md)). October 2026 fixed cost in `eu-west-1` was roughly **RDS ~$15.80**, **VPC endpoints ~$24.55**, and **RDS Secrets Manager secret ~$0.40** (~**$40.75/mo** pre-tax regardless of traffic).

We need a relational store that preserves SQL, ~160 repository methods, foreign keys, partial unique indexes, and `ON CONFLICT` patterns—not a greenfield NoSQL rewrite—while eliminating idle VPC/RDS overhead before launch.

**Pre-launch posture:** no customer data migration, no dual-write, no backfill, and no copy from RDS into DSQL; DSQL starts from a **fresh DSQL-native schema**. **RDS remains production** until workstream **DSQL-8** cuts prod over; existing RDS data may be abandoned at cutover.

## Decision

Adopt **Amazon Aurora DSQL** (PostgreSQL-compatible, public endpoint, IAM auth, Lambdas **outside** a VPC after cutover) as the **next** canonical catalog store. Execution is phased in workstreams **DSQL-0 … DSQL-9** ([mega-plan](../../plans/aurora-dsql-migration-mega-plan.md)).

### DSQL-0 (this ADR’s immediate slice)

- Record the decision here; supersede [ADR-0008](./adr-0008-dynamodb-to-rds-migration.md); amend [ADR-0010](./adr-0010-lesson-progress-rds.md), [ADR-0012](./adr-0012-api-abuse-protection.md), [ADR-0013](./adr-0013-one-time-purchases-bundle-entitlements.md).
- **Freeze** [`infrastructure/database/migrations/`](../../infrastructure/database/migrations/) at **24** SQL files (no new migrations until DSQL-native schema in DSQL-1).
- **Remove** the CloudWatch **Logs** VPC interface endpoint (DSQL-0 cost trim); catalog logging uses Lambda’s managed delivery, not the ENI Logs API.
- **RDS automated backup retention: 1 day** pre-launch (operator override documented here; `DeletionPolicy: Snapshot` on stack delete unchanged until DSQL-9).

### Cluster, schema, and rollout (DSQL-1+; finalized in mega-plan §3.2)

| Id | Decision |
|----|----------|
| **D1 — Clusters** | One single-Region DSQL cluster in `eu-west-1` (`infrastructure/templates/dsql-stack.yaml`), deletion protection on, `DeletionPolicy: Retain`. |
| **D2 — Schema** | Application objects in schema **`app`** (admin manages `public` and owns all objects in **`app`**). |
| **D3 — DB roles** | CI schema/admin jobs use **admin** IAM connect only. Runtime Lambdas use **`smc_app`**: `AWS IAM GRANT smc_app TO '<deploy-role-arn>'`, cluster IAM **`dsql:DbConnect`**, and **`USAGE` on schema `app`** plus **`SELECT, INSERT, UPDATE, DELETE` on all tables in `app`** (no `CREATE`/`DROP`/`TRUNCATE`). Spike + applier grant that shape; ownership stays on admin. |
| **D4 — Network** | Public endpoint, TLS, IAM auth; optional resource policy limiting to account roles. |
| **D5 — Backups** | None on DSQL pre-launch (no AWS Backup plan for DSQL). |
| **D6 — Transitional preview API** | **`StreamMyCourse-Api-dsql`**: same catalog code, **no VPC**, env **`DSQL_ENDPOINT`** instead of **`DB_HOST`/`DB_*`**, own API stage—created DSQL-1, deleted DSQL-9. Sanctioned, time-bounded exception to [no-feature-flags-by-default](../../.cursor/rules/no-feature-flags-by-default.mdc): `bootstrap.py` picks the connection factory by **which dependency is configured**, not an on/off flag. |

Prod integration and deploy jobs continue to target **`StreamMyCourse-Api-prod` (RDS)** until **DSQL-8**.

## Alternatives considered

| Option | Why not (pre-launch) |
|--------|----------------------|
| **DynamoDB single-table** | Similar idle cost at this scale but **high** rewrite cost and weaker DB-enforced integrity for purchases, quizzes, and progress. |
| **Keep RDS, trim endpoints only** | Still pays instance + remaining endpoints; Logs removal is part of DSQL-0 anyway. |
| **Aurora Serverless v2 + Data API** | Cold resume and adapter churn vs psycopg2-style repos. |
| **Public RDS without VPC** | Unstable Lambda egress + security posture rejected in ADR-0008; keeps instance cost. |
| **Big-bang flip (no preview stack)** | No per-workstream HTTPS E2E gate against real DSQL before prod cutover. |

See [mega-plan §9](../../plans/aurora-dsql-migration-mega-plan.md) for cost tables and compatibility audit pointers.

## Consequences

### Pros

- Near **$0/mo** DSQL idle cost at current traffic vs ~$40/mo VPC+RDS fixed burn.
- SQL port, not a domain rewrite; FK/cascade model largely preserved (with DSQL transaction caps and OCC retry layer in DSQL-1).
- Preview stack enables integration tests per workstream before DSQL-8.

### Cons

- Multi-month migration; dual operational footprint (RDS prod + DSQL preview) until DSQL-8.
- DSQL caps (e.g. 3,000 modified rows per transaction, 60-minute connection lifetime) require batched deletes and OCC retries.
- Cognito triggers stay on RDS until DSQL-8 (documented in mega-plan §0.4).

## Follow-ups

- DSQL-1: cluster, `infrastructure/database/dsql/`, preview stack, connection layer.
- DSQL-8: prod cutover; DSQL-9: delete RDS, VPC, preview stack; set this ADR to **Accepted**.
- [`module-map.md`](./module-map.md), [`design.md`](../../design.md) §6/§9/§10: narrow DSQL-0 updates; full rewrite in DSQL-9.

## Related

- **Supersedes:** [ADR-0008](./adr-0008-dynamodb-to-rds-migration.md) (next-store decision only; RDS still live until DSQL-8).
- **Amends:** [ADR-0010](./adr-0010-lesson-progress-rds.md), [ADR-0012](./adr-0012-api-abuse-protection.md), [ADR-0013](./adr-0013-one-time-purchases-bundle-entitlements.md).
- [Aurora DSQL user guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/) · [pricing](https://aws.amazon.com/rds/aurora/dsql/pricing/).
