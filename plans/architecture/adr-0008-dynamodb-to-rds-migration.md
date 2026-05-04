# ADR 0008 — DynamoDB-to-RDS PostgreSQL migration

## Status

Proposed (code landed, cutover pending)

## Context

The MVP catalog was implemented on a single DynamoDB table (see
[ADR 0001](./adr-0001-single-table-dynamodb.md) and
[ADR 0006](./adr-0006-dynamo-access-evolution.md)). That design was correct
for the original scope — a handful of access patterns per course, Scan-free
reads, and near-zero operational overhead.

Phase 2 (`roadmap.md`) introduces:

1. **Teacher dashboards** — earnings, enrollment counts, course-level
   completion rate, per-lesson engagement. These are aggregation/analytics
   queries across entities that DynamoDB cannot serve without pre-computed
   materialized views or an external analytics store.
2. **Payments / payouts** — multi-row ACID transactions that span courses,
   enrollments, and ledger entries. DynamoDB transactions exist
   (`TransactWriteItems`, 100-op limit) but require significant item-shape
   gymnastics to satisfy both the MVP access patterns and the payment flows
   in the same table.

A relational store is the natural fit for both use cases and avoids layering
a second database (e.g. DynamoDB + RDS) purely for analytics. `design.md`
already nominates **RDS PostgreSQL** for the Phase 2 workloads; migrating the
MVP catalog to the same store now keeps the system on a single data plane
instead of splitting it.

Constraints baked into this decision:

- **Scale:** ≤200 non-concurrent users today, ~1K users near-term.
- **Cost:** No NAT Gateway (~$32/month); cheapest viable RDS profile.
- **Ops overhead:** Single-engineer team; avoid PgBouncer/RDS Proxy until
  concurrency warrants it.
- **Rollback:** Changing a primary store is high-risk — we need an instant
  rollback path and a bake period.

## Decision

Move the catalog's persistence layer from a DynamoDB single-table design to
**RDS PostgreSQL (`db.t4g.micro`)** behind the existing repository ports.
The switch is controlled by a `USE_RDS` feature flag so DynamoDB stays as
the rollback path for the duration of the bake period.

### Infrastructure

A new stack `infrastructure/templates/rds-stack.yaml` provisions:

- **VPC (1 AZ)** with a private subnet holding the RDS instance and the
  Lambda ENIs. A tiny second private subnet in AZ-b is created only to
  satisfy the `DBSubnetGroup` multi-AZ requirement (no resources placed
  there; zero cost).
- **RDS `db.t4g.micro`** — PostgreSQL 16, encrypted at rest, not publicly
  accessible, `BackupRetentionPeriod=7` in prod / 1 elsewhere,
  `DeletionPolicy: Snapshot`.
- **Secrets Manager secret** (`streammycourse/<env>/rds-credentials`) with
  an auto-generated 32-char password attached to the RDS instance via
  `AWS::SecretsManager::SecretTargetAttachment`.
- **VPC interface endpoints** for Secrets Manager and CloudWatch Logs
  (~$7.20/mo each in one AZ).
- **VPC gateway endpoints** for S3 and DynamoDB (free). S3 is needed for
  presigned URLs; DynamoDB is retained during the rollback window.
- **Security groups:** Lambda SG (egress only), RDS SG (ingress 5432 from
  Lambda SG), Endpoint SG (ingress 443 from Lambda SG).

`api-stack.yaml` gains two parameters (`RdsStackName`, `UseRds`), a
`VpcConfig` block that imports the Lambda SG and private subnet from the RDS
stack, RDS-related env vars fed from cross-stack exports, and a
`secretsmanager:GetSecretValue` policy scoped to the specific secret ARN.
The Lambda timeout moves from 15s to 30s to absorb the VPC ENI-attach cold
start.

### Data plane

The database schema (`infrastructure/database/migrations/001_initial_schema.sql`)
mirrors the DynamoDB row shapes: `courses`, `lessons`, `users`, `enrollments`.
`lessons.course_id` cascades on delete; `enrollments` has a composite PK and a
`course_id` index for reverse lookups (teacher dashboards).

The clean-architecture layering (controller → service → repo) made the
adapter swap straightforward. New PostgreSQL adapters live alongside the
DynamoDB ones:

| Bounded context | DynamoDB adapter | PostgreSQL adapter |
|-----------------|------------------|-------------------|
| `course_management` | `repo.py` (`CourseCatalogRepository`) | `rds_repo.py` (`CourseCatalogRdsRepository`) |
| `enrollment` | `repo.py` (`EnrollmentRepository`) | `rds_repo.py` (`EnrollmentRdsRepository`) |
| `auth` | `repo.py` (`UserProfileRepository`) | `rds_repo.py` (`UserProfileRdsRepository`) |

Ports stay unchanged. The service layer is untouched. A new
`services/auth/ports.py` was added to introduce `UserProfileRepositoryPort`
(the DynamoDB auth adapter was previously imported concretely from
`service.py`).

`bootstrap.py` picks the adapter set based on `cfg.use_rds` and lazily opens
a single psycopg2 connection per warm Lambda container. Adapters retry once
on `OperationalError` to cover RDS idle-timeouts without a user-visible 500.

### Key engineering choices

- **psycopg2 directly, not SQLAlchemy.** Smaller Lambda zip, fewer deps,
  queries already look like parameterized SQL in the DynamoDB adapter.
- **Parameterized SQL everywhere.** Every adapter uses `%s` placeholders;
  no f-strings into SQL (CI boundary + hand review).
- **camelCase ↔ snake_case translation in each adapter.** Column names are
  snake_case in SQL; domain models and dict contracts are camelCase. One
  `_row_to_<type>` helper per adapter keeps the mapping in one place.
- **UUID → str casting at the adapter boundary.** psycopg2 returns
  `uuid.UUID` objects; the domain models are `str`-typed. Casting in the
  helpers keeps the rest of the stack unaware.
- **Lambda in VPC, private RDS, interface endpoints.** Non-VPC Lambda has
  unpredictable egress IPs that cannot be allowlisted; public RDS behind
  SG was considered and rejected (would require `0.0.0.0/0`). VPC is
  mandatory. NAT Gateway is avoided by using interface/gateway endpoints
  for the SDKs the Lambda actually uses.
- **Vendored psycopg2 via `deploy-backend.sh`.** The script stages the
  Lambda source into a build dir, runs `pip install -r requirements.txt
  -t _vendor --platform manylinux2014_x86_64 --only-binary=:all:
  --python-version 3.11`, and zips. `_vendor/` is gitignored;
  `index.py` prepends it to `sys.path` at cold start.

## Consequences

**Pros**
- Relational queries (joins, aggregates, window functions) are finally on
  the menu — teacher dashboards do not need a second data store.
- ACID transactions work naturally for upcoming payments without
  item-shape contortions.
- Schema is self-documenting and explicit; no more hidden access-pattern
  coupling in the PK/SK scheme.
- CI boundary script enforces that `psycopg2` only appears in
  `rds_repo.py` or `bootstrap.py`.

**Cons**
- Fixed VPC cost (~$14.80/mo in 1-AZ) that DynamoDB did not have.
- Single-AZ means the VPC endpoints and RDS are unavailable in an AZ
  outage. Acceptable for the current scale; revisit when SLA becomes a
  concern.
- Connection lifecycle adds a moving part: `db.t4g.micro` caps around 65
  connections. Lambda reserved concurrency may need tuning if peak
  concurrency climbs.
- Cold starts lengthen by ~1–2s (ENI attach + first Secrets Manager fetch).
  Timeout bumped from 15s to 30s to absorb this.
- Two adapter implementations per bounded context during the bake window.
  After the bake, the DynamoDB adapters and the catalog table are
  candidates for removal.

## Alternatives considered

**Aurora Serverless v2 (PostgreSQL-compatible).** Data API would have
removed the VPC/ENI coupling entirely, but Data API only works for Aurora
(not standard RDS) and carries a minimum cost (~$43/mo at 0.5 ACU) that
exceeds our current burn. Defer until usage justifies.

**DynamoDB + a separate analytics store (Athena/Timestream).** Kept the
MVP happy path untouched but doubled the data plane, required ETL, and
did not solve the payments transaction problem. Rejected.

**Stay on DynamoDB and build the dashboards with materialized aggregates.**
Technically possible but every new aggregate is bespoke item-shape
engineering. Costs the team more than a relational schema over time.
Rejected.

## Follow-ups

- Remove `table_name` / DynamoDB policy / `CatalogTable` from `api-stack.yaml`
  after bake. Track in `roadmap.md`.
- Introduce a schema migration tool (Flyway / Alembic) when the third
  `00X_*.sql` file lands; 001 was applied manually via psql.
- Extend the deploy-role inline policy so CI can manage the rds-stack
  resources (RDS, VPC, Secrets Manager, VPC endpoints).
- Revisit RDS Proxy / pgbouncer when Lambda concurrency exceeds ~50
  sustained.

## Related

- [ADR 0001 — Single-table DynamoDB for the MVP catalog](./adr-0001-single-table-dynamodb.md)
- [ADR 0006 — Data access evolution](./adr-0006-dynamo-access-evolution.md)
- [`design.md`](../../design.md) §6 (Data), §10 (Deployment)
- [`roadmap.md`](../../roadmap.md) — Phase 2 payments and analytics
