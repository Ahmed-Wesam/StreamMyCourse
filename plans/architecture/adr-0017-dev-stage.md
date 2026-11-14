# ADR 0017 — Optional dev AWS stage (isolated DSQL, manual dispatch)

## Status

**Accepted** (workflow and templates **2026-11-14**; four dev stacks **CREATE/UPDATE_COMPLETE** after [Deploy dev **43596012266**](https://github.com/Ahmed-Wesam/StreamMyCourse/actions/runs/43596012266))

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

The first dispatch ([Deploy dev **43564776149**](https://github.com/Ahmed-Wesam/StreamMyCourse/actions/runs/43564776149)) stopped at **`guard-dev-google`** because Environment **`dev`** had no Google secrets. A later dispatch ([**43594755794**](https://github.com/Ahmed-Wesam/StreamMyCourse/actions/runs/43594755794)) created the DSQL cluster and schema, then failed in Auth because S3 upload progress was parsed as the package key. [`da1007f`](https://github.com/Ahmed-Wesam/StreamMyCourse/commit/da1007f) fixed that. [Deploy dev **43596012266**](https://github.com/Ahmed-Wesam/StreamMyCourse/actions/runs/43596012266) completed.

`describe-stacks` in `eu-west-1` after that run:

| Stack | Status |
|-------|--------|
| `StreamMyCourse-Dsql-dev` | `CREATE_COMPLETE` (cluster `xnuhmtafzjya4cdlho5ex66owu`, not the prod cluster) |
| `StreamMyCourse-Auth-dev` | `UPDATE_COMPLETE` (hosted UI `streammycourse-auth-dev-878564870560.auth.eu-west-1.amazoncognito.com`) |
| `StreamMyCourse-Api-dev` | `CREATE_COMPLETE` (`https://6fdkylrhwf.execute-api.eu-west-1.amazonaws.com/dev`) |
| `StreamMyCourse-DevVideo-dev` | `CREATE_COMPLETE` |

Signed-out `GET /dev/courses` returned `[]`. Signed-out `GET /prod/courses` also returned `[]`. `StreamMyCourse-Dsql-prod` stayed `CREATE_COMPLETE`.

## Consequences

- The four dev stacks exist and use a Google client that is not the prod client. Local Vite still defaults to the prod API.
- Integration tests and **Deploy** on **`main`** remain **prod-only**.
- Operators must create a **separate** Google OAuth client for **`dev`**; copying prod values is blocked by design.

## Related

- [ADR-0016](./adr-0016-rds-postgresql-to-aurora-dsql.md) — prod Aurora DSQL
- [`design.md`](../../design.md) §10 — environment model