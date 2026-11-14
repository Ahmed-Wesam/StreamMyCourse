# ADR 0016 — RDS PostgreSQL → Aurora DSQL (cost-driven, pre-launch)

## Status

**Accepted** (DSQL-8 prod cutover **2026-11-13**; DSQL-9 decommission **2026-11-14**)

## Outcome (DSQL-9)

Operator and CI deleted **`StreamMyCourse-Rds-prod`** (no final RDS snapshot — pre-launch, no customer data), the RDS VPC and interface/gateway endpoints, **`StreamMyCourse-RdsQuery-prod`**, and transitional preview **`StreamMyCourse-Api-dsql`**. **`StreamMyCourse-Dsql-prod`** remains with deletion protection; prod catalog, Cognito UserProfileSync, and BillingFulfillment use **`DSQL_ENDPOINT`** only (no `VpcConfig`). Catalog Lambda timeout is **20 s** (no VPC ENI). Repo and Deploy removed RDS connection/bootstrap, RDS CI jobs, and `verify-rds-reusable.yml`; persistence smoke is [`test_persistence_smoke.py`](../../tests/integration/test_persistence_smoke.py) with GitHub **`COGNITO_VERIFY_*`** secrets.

## Context

StreamMyCourse is **pre-launch** (no customers). Through **2026-11-12**, the catalog, rate limits, purchases, and analytics lived on **RDS PostgreSQL** inside a private VPC with interface/gateway endpoints (see [ADR-0008](./adr-0008-dynamodb-to-rds-migration.md)). October 2026 fixed cost in `eu-west-1` was roughly **RDS ~$15.80**, **VPC endpoints ~$24.55**, and **RDS Secrets Manager secret ~$0.40** (~**$40.75/mo** pre-tax regardless of traffic).

We needed a relational store that preserves SQL, ~160 repository methods, foreign keys, partial unique indexes, and `ON CONFLICT` patterns—not a greenfield NoSQL rewrite—while eliminating idle VPC/RDS overhead before launch.

**Pre-launch posture:** no customer data migration, no dual-write, no backfill, and no copy from RDS into DSQL; DSQL started from a **fresh DSQL-native schema**. **RDS was production until DSQL-8**; existing RDS data was abandoned at cutover.

## Decision

Adopt **Amazon Aurora DSQL** (PostgreSQL-compatible, public endpoint, IAM auth, Lambdas **outside** a VPC) as the **canonical catalog store**. Execution was phased in workstreams **DSQL-0 … DSQL-9** ([mega-plan](../../plans/aurora-dsql-migration-mega-plan.md) — not edited here).

### DSQL-0 (immediate slice)

- Record the decision here; supersede [ADR-0008](./adr-0008-dynamodb-to-rds-migration.md); amend [ADR-0010](./adr-0010-lesson-progress-rds.md), [ADR-0012](./adr-0012-api-abuse-protection.md), [ADR-0013](./adr-0013-one-time-purchases-bundle-entitlements.md).
- **Freeze** [`infrastructure/database/migrations/`](../../infrastructure/database/migrations/) at **24** SQL files (no new migrations; historical reference after DSQL-9).
- **Remove** the CloudWatch **Logs** VPC interface endpoint (DSQL-0 cost trim); catalog logging uses Lambda’s managed delivery, not the ENI Logs API.
- **RDS automated backup retention: 1 day** pre-launch (operator override documented here; stack deleted DSQL-9 without final snapshot).

### Cluster, schema, and rollout (DSQL-1+)

| Id | Decision |
|----|----------|
| **D1 — Clusters** | One single-Region DSQL cluster in `eu-west-1` (`infrastructure/templates/dsql-stack.yaml`), deletion protection on, `DeletionPolicy: Retain`. |
| **D2 — Schema** | Application objects in schema **`app`** (admin manages `public` and owns all objects in **`app`**). |
| **D3 — DB roles** | CI schema/admin jobs use **admin** IAM connect only. Runtime Lambdas use **`smc_app`**: `AWS IAM GRANT smc_app TO '<deploy-role-arn>'`, cluster IAM **`dsql:DbConnect`**, and **`USAGE` on schema `app`** plus **`SELECT, INSERT, UPDATE, DELETE` on all tables in `app`** (no `CREATE`/`DROP`/`TRUNCATE`). Spike + applier grant that shape; ownership stays on admin. |
| **D4 — Network** | Public endpoint, TLS, IAM auth; optional resource policy limiting to account roles. |
| **D5 — Backups** | None on DSQL pre-launch (no AWS Backup plan for DSQL). |
| **D6 — Transitional preview API** | **`StreamMyCourse-Api-dsql`** — sanctioned, time-bounded exception for HTTPS gates before prod cutover (**deleted DSQL-9**). Prod uses **`StreamMyCourse-Api-prod`** on DSQL only. |

## Alternatives considered

| Option | Why not (pre-launch) |
|--------|----------------------|
| **DynamoDB single-table** | Similar idle cost at this scale but **high** rewrite cost and weaker DB-enforced integrity for purchases, quizzes, and progress. |
| **Keep RDS, trim endpoints only** | Still pays instance + remaining endpoints; Logs removal was part of DSQL-0 anyway. |
| **Aurora Serverless v2 + Data API** | Cold resume and adapter churn vs psycopg2-style repos. |
| **Public RDS without VPC** | Unstable Lambda egress + security posture rejected in ADR-0008; keeps instance cost. |
| **Big-bang flip (no preview stack)** | No per-workstream HTTPS E2E gate against real DSQL before prod cutover. |

See [mega-plan §9](../../plans/aurora-dsql-migration-mega-plan.md) for cost tables and compatibility audit pointers.

## Consequences

### Pros

- Near **$0/mo** DSQL idle cost at current traffic vs ~$40/mo VPC+RDS fixed burn (RDS path removed).
- SQL port, not a domain rewrite; FK/cascade model largely preserved (with DSQL transaction caps and OCC retry layer in DSQL-1).
- Preview stack enabled integration tests per workstream before DSQL-8 (retired DSQL-9).

### Cons

- Multi-month migration (complete **2026-11-14**).
- DSQL caps (e.g. 3,000 modified rows per transaction, 60-minute connection lifetime) require batched deletes and OCC retries.
- Catalog, sync, and fulfillment share the public DSQL endpoint; edge workers (Kinescope, mail, billing HTTP) remain **non-VPC** by design.

## Follow-ups

- **Operator docs:** [`design.md`](../../design.md), [`module-map.md`](./module-map.md), [`infrastructure/docs/dsql-query-runbook.md`](../../infrastructure/docs/dsql-query-runbook.md) — prod is DSQL-only.
- **Optional ADR later:** document the **edge worker / no-NAT** inventory (mail, media cleanup, video provider edge, billing edge) as a single security-boundary narrative if the team wants it separate from this store decision.

## Related

- **Supersedes:** [ADR-0008](./adr-0008-dynamodb-to-rds-migration.md) (next-store decision; RDS decommissioned DSQL-9).
- **Amends:** [ADR-0010](./adr-0010-lesson-progress-rds.md), [ADR-0012](./adr-0012-api-abuse-protection.md), [ADR-0013](./adr-0013-one-time-purchases-bundle-entitlements.md).
- [Aurora DSQL user guide](https://docs.aws.amazon.com/aurora-dsql/latest/userguide/) · [pricing](https://aws.amazon.com/rds/aurora/dsql/pricing/).