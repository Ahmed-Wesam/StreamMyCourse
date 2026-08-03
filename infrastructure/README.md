# StreamMyCourse - Infrastructure

AWS infrastructure managed via CloudFormation. **Deployed CI/CD and integration tests target prod only** (`StreamMyCourse-*-prod`, region `eu-west-1`; edge hosting in `us-east-1`).

## Prerequisites

1. **AWS CLI installed** (v2 recommended)
2. **AWS credentials configured**

## Quick Start

### 1. Configure AWS credentials

Use **`eu-west-1`** as the default region for StreamMyCourse stacks.

```powershell
aws configure
```

Or SSO:

```powershell
aws sso login --profile your-profile
```

### 2. (Optional) Billing alarm stack

```powershell
cd infrastructure
.\deploy.ps1 -Template billing -StackName streammycourse-billing -EmailAddress "your@email.com"
```

Enable **Receive Billing Alerts** under **Billing** → **Billing preferences** in the AWS console.

### 3. Deploy backend and web

Prefer **GitHub Actions** on `main` (see below). For local deploys:

| Goal | Command |
|------|---------|
| Video bucket + API for **prod** | `./scripts/deploy-backend.sh prod` (from repo root) |
| One template only (api, video, web, web-cert, billing, edge-hosting) | `.\deploy.ps1 -Template <name> -StackName <name> …` (see script parameters) |

There is **no dummy / test stack** in this repo (the old `dummy-stack.yaml` was removed).

### 4. Delete a CloudFormation stack

Use the AWS CLI (replace stack name and region as needed):

```powershell
aws cloudformation delete-stack --stack-name YOUR_STACK --region eu-west-1
aws cloudformation wait stack-delete-complete --stack-name YOUR_STACK --region eu-west-1
```

Or `.\deploy.ps1 -Delete -StackName YOUR_STACK -Template api -Region eu-west-1` (a valid `-Template` is still required so the script can resolve paths before `-Delete` runs).

### 5. Prod stack map

| Piece | Prod stack / resource |
|--------|----------------------|
| Video (S3) | `StreamMyCourse-Video-prod` |
| API + catalog | `StreamMyCourse-Api-prod` |
| Auth (Cognito) | `StreamMyCourse-Auth-prod` |
| RDS | `StreamMyCourse-Rds-prod` |
| RDS query helper | `StreamMyCourse-RdsQuery-prod` |
| Media cleanup | `StreamMyCourse-MediaCleanup-prod` |
| Payments / billing edge | `StreamMyCourse-Payments-prod` |
| Video provider edge (Kinescope) | `StreamMyCourse-VideoProviderEdge-prod` |
| SPA + ACM edge | `StreamMyCourse-EdgeHosting-prod` (**us-east-1**) |
| Legacy split stacks (optional) | `StreamMyCourse-Web-prod` / `TeacherWeb-prod` / `Cert-prod` in older accounts |

**Deploy backend (prod):**

```bash
./scripts/deploy-backend.sh prod
```

**Deploy / update SPA** (build + S3 + CloudFront invalidation) — pass the **ApiEndpoint** from `StreamMyCourse-Api-prod`:

```powershell
aws cloudformation describe-stacks --stack-name StreamMyCourse-Api-prod --region eu-west-1 --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text
```

**CI/CD:** On every **full** [`.github/workflows/deploy-backend.yml`](../.github/workflows/deploy-backend.yml) run, **`deploy-edge-prod`** runs **`edge-hosting-stack.yaml`** as **`StreamMyCourse-EdgeHosting-prod`** in **`us-east-1`**, then reusable workflows sync assets to the **output buckets**. Migration from legacy three stacks: [`edge-hosting-migration.md`](docs/edge-hosting-migration.md).

**Lower-level API deploy:**

```powershell
.\deploy.ps1 -Template api -StackName StreamMyCourse-Api-prod -Environment prod `
  -VideoBucketName YOUR_BUCKET -VideoUrl "https://YOUR_BUCKET.s3.REGION.amazonaws.com" `
  -CorsAllowOrigin "https://researchspectrum.org,https://teach.researchspectrum.org,http://localhost:5173,http://localhost:5174" -GatewayResponseAllowOrigin 'https://researchspectrum.org'
```

Optional **`deploy.ps1`** API parameters: `-VideoUrl`, `-DefaultMp4Url` (passed through to CloudFormation).

## Phase 0 — AWS teardown (legacy dev stacks)

Use this when removing **old `*-dev`** resources after the prod-only cutover. **Double-check account, region, and stack names** before destructive steps. Take RDS snapshots before prod touches.

**Recommended delete order** (dependents first; wait for each `stack-delete-complete`):

| Order | Region | Stack / action |
|-------|--------|----------------|
| 1 | `eu-west-1` | WAF: `StreamMyCourse-ApiWaf-dev` (if present) — or run [`scripts/delete-waf-stacks.sh`](../scripts/delete-waf-stacks.sh) after disassociating prod WAF only |
| 2 | `us-east-1` | WAF: `StreamMyCourse-EdgeWaf-dev` (if present) |
| 3 | `eu-west-1` | `StreamMyCourse-Api-dev` or legacy **`streammycourse-api`** |
| 4 | `eu-west-1` | `StreamMyCourse-Payments-dev`, `StreamMyCourse-MediaCleanup-dev`, `StreamMyCourse-VideoProviderEdge-dev` |
| 5 | `eu-west-1` | `StreamMyCourse-Auth-dev` |
| 6 | `eu-west-1` | `StreamMyCourse-Video-dev` (bucket has **Retain** — empty or migrate objects separately) |
| 7 | `eu-west-1` | `StreamMyCourse-RdsQuery-dev`, then `StreamMyCourse-Rds-dev` (**snapshot first** if keeping data) |
| 8 | `us-east-1` | `StreamMyCourse-EdgeHosting-dev` |
| 9 | `eu-west-1` | Legacy `StreamMyCourse-Web-dev`, `StreamMyCourse-TeacherWeb-dev`, `StreamMyCourse-Cert-dev` |
| 10 | `eu-west-1` | `StreamMyCourse-ArtifactJanitor-dev`, `StreamMyCourse-RdsWipe-dev` (if any remain) |

**GitHub:** Remove the **`dev`** GitHub Environment (secrets/variables) after prod secrets are verified. Copy any prod-only values using [`scripts/set-github-auth-secrets-from-stack.ps1`](../scripts/set-github-auth-secrets-from-stack.ps1) with `-Environment prod`.

**DNS:** Remove Route 53 aliases for `dev.researchspectrum.org` / `teach.dev.researchspectrum.org` when no longer needed.

## GitHub Actions — automated deploys

**Every push to `main`** runs the **prod** pipeline: edge + RDS + backend + integration HTTP tests + verify RDS + SPAs. See [`.github/workflows/deploy-backend.yml`](../.github/workflows/deploy-backend.yml). **`cancel-in-progress: false`**: rapid commits **queue**. Lambda code is uploaded as **`catalog-prod-{gitSha12}.zip`**.

### Secrets and variables (deploy workflows)

| Name | Kind | What it is | Where to get it |
|--------|------|------------|-----------------|
| **`AWS_DEPLOY_ROLE_ARN`** | **Repository Actions variable** (required) | IAM role ARN for OIDC | [`templates/github-deploy-role-stack.yaml`](templates/github-deploy-role-stack.yaml) output **`GitHubDeployRoleArn`** |
| **`VITE_API_BASE_URL`** | API base URL **no trailing slash** | Set on GitHub Environment **`prod`** from **`StreamMyCourse-Api-prod`** **ApiEndpoint** |

### GitHub Environment variables (backend / edge deploy)

Set on GitHub Environment **`prod`**:

| Variable | Purpose |
|----------|---------|
| **`COGNITO_DOMAIN_PREFIX`** | **Required** for full deploy. Globally unique Cognito hosted UI prefix. |
| **`ROUTE53_HOSTED_ZONE_ID`** | Route 53 hosted zone for DNS validation and alias records. |
| **`STUDENT_WEB_DOMAIN`** | Student SPA hostname (e.g. `researchspectrum.org`). |
| **`TEACHER_WEB_DOMAIN`** | Teacher SPA hostname (e.g. `teach.researchspectrum.org`). |
| **`WEB_CERT_DOMAIN`** | Optional ACM primary name override. |
| **`WEB_CERT_SANS`** | Optional comma-separated SANs on the ACM cert. |

Callback / logout URL variables for Cognito (`STUDENT_COGNITO_*`, `TEACHER_COGNITO_*`) and Google IdP secrets are unchanged; see workflow `env` blocks in `deploy-backend.yml`.

### GitHub OIDC deploy role (CloudFormation bootstrap — not in CI/CD)

**Preferred:** deploy the IAM stack **locally** (admin credentials). This is **not** invoked from GitHub Actions.

```bash
chmod +x scripts/deploy-github-iam-stack.sh
./scripts/deploy-github-iam-stack.sh
```

After deploy, copy **`GitHubDeployRoleArn`** from stack outputs into **`AWS_DEPLOY_ROLE_ARN`**.

**Alternative (policy-only touch):** `./scripts/apply-github-deploy-role-policies.sh` or `.\scripts\apply-github-deploy-role-policies.ps1`

### `deploy-backend.yml`

[`.github/workflows/deploy-backend.yml`](../.github/workflows/deploy-backend.yml) — **`deploy-edge-prod`** runs [`scripts/deploy-edge.sh`](../scripts/deploy-edge.sh). **`deploy-backend-prod`** runs Cognito (auth) then [`scripts/deploy-backend.sh`](../scripts/deploy-backend.sh). Student and teacher asset deploys use reusable workflows after integration tests pass.

### `deploy-web.yml` + `deploy-web-reusable.yml`

Manual SPA-only deploys: [`.github/workflows/deploy-web.yml`](../.github/workflows/deploy-web.yml) targets **prod** via [`.github/workflows/deploy-web-reusable.yml`](../.github/workflows/deploy-web-reusable.yml).

**No extra secrets for site bucket or CloudFront ID** — read from **`StreamMyCourse-EdgeHosting-prod`** stack outputs.

## Directory Structure

```
infrastructure/
├── templates/
│   ├── api-stack.yaml        # API Gateway + Lambda + RDS wiring
│   ├── edge-hosting-stack.yaml # Unified ACM + both SPAs (us-east-1); primary CI path
│   ├── github-deploy-role-stack.yaml # GitHub OIDC deploy role + policies (manual bootstrap only)
│   └── ...
├── deploy.ps1                 # Single-template deploy (api, web, edge-hosting, video, …)
└── README.md                  # This file

See also at repo root: [`scripts/deploy-backend.sh`](../scripts/deploy-backend.sh) (Lambda + video + API), [`scripts/deploy-edge.sh`](../scripts/deploy-edge.sh) (cert + student/teacher web CF for CI), [`scripts/deploy-github-iam-stack.sh`](../scripts/deploy-github-iam-stack.sh) / [`.ps1`](../scripts/deploy-github-iam-stack.ps1), and [`scripts/apply-github-deploy-role-policies.sh`](../scripts/apply-github-deploy-role-policies.sh) / [`.ps1`](../scripts/apply-github-deploy-role-policies.ps1).
```

## Roadmap / future infra

Post-MVP templates and services are described in [`roadmap.md`](../roadmap.md).

## Cost warning

MVP stacks aim for free-tier–friendly usage. The API stack has no S3 triggers or schedules, which avoids runaway automation.
