# ADR 0017 — Optional dev AWS stage (isolated DSQL, manual dispatch)

## Status

**Accepted** (workflow and templates **2026-11-14**; **no dev stacks** created until Environment **`dev`** has distinct Google OAuth secrets)

## Context

Engineers need an isolated **`dev`** API and Cognito pool for localhost work without writing prod DSQL data. Cost must stay low: no second CloudFront, VPC, RDS, HyperPay, Zoho, or Kinescope on dev. Customer traffic remains on **`prod`** (`researchspectrum.org`, `StreamMyCourse-Api-prod`).

## Decision

| Area | Choice |
|------|--------|
| **Trigger** | [`.github/workflows/deploy-dev.yml`](../../.github/workflows/deploy-dev.yml) — **`workflow_dispatch` only**; does not run on push and does not modify [`deploy-backend.yml`](../../.github/workflows/deploy-backend.yml). |
| **Script** | [`scripts/deploy-dev.sh`](../../scripts/deploy-dev.sh) (`dev` + `dsql\|schema\|auth\|video\|api`); guards and parameter builders in [`scripts/dev_stage.py`](../../scripts/dev_stage.py). |
| **Stacks (intended)** | `StreamMyCourse-Dsql-dev`, `StreamMyCourse-Auth-dev`, `StreamMyCourse-Api-dev`, `StreamMyCourse-DevVideo-dev` (S3-only [`dev-video-bucket-stack.yaml`](../../infrastructure/templates/dev-video-bucket-stack.yaml)). |
| **DSQL** | Same [`dsql-stack.yaml`](../../infrastructure/templates/dsql-stack.yaml) with `Environment=dev`; prod cluster id is denied in `dev_stage.py`. |
| **Auth** | Shared [`auth-stack.yaml`](../../infrastructure/templates/auth-stack.yaml) with `Environment=dev`, separate Google client (not prod), Zoho custom sender off, profile sync on. |
| **Video** | `VIDEO_PROVIDER=s3` and dev bucket only — not [`video-stack.yaml`](../../infrastructure/templates/video-stack.yaml) (CloudFront). |
| **Local Vite** | Default proxy stays **prod** API; dev API is opt-in via env ([`frontend/.env.example`](../../frontend/.env.example)). |
| **Google guard** | Hash job on Environment **`prod`** outputs SHA-256 only; guard job on **`dev`** refuses missing secrets or digest match before any AWS create. |

## Observed state (2026-11-14)

After the first dispatch ([Deploy dev **43564776149**](https://github.com/Ahmed-Wesam/StreamMyCourse/actions/runs/43564776149)):

- **`guard-dev-google` failed** — Environment **`dev`** secrets **`GOOGLE_OAUTH_CLIENT_ID`** and **`GOOGLE_OAUTH_CLIENT_SECRET`** were not set.
- **No CloudFormation stacks** — `describe-stacks` in `eu-west-1` reported no `StreamMyCourse-Dsql-dev`, `StreamMyCourse-Auth-dev`, `StreamMyCourse-Api-dev`, or `StreamMyCourse-DevVideo-dev`.

Prod **Deploy** on commit `eac2fcf` completed successfully; `StreamMyCourse-Dsql-prod` was updated in place (tag parameter only; no cluster replacement).

## Consequences

- Dev stage is **not shipped** until all four stacks exist and operators set dev Google credentials.
- Integration tests and **Deploy** on **`main`** remain **prod-only**.
- Operators must create a **separate** Google OAuth client for **`dev`**; copying prod values is blocked by design.

## Related

- [ADR-0016](./adr-0016-rds-postgresql-to-aurora-dsql.md) — prod Aurora DSQL
- [`design.md`](../../design.md) §10 — environment model