# StreamMyCourse - Infrastructure

AWS infrastructure managed via CloudFormation.

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
| Video bucket + API for **dev** or **prod** | `.\deploy-environment.ps1 -Environment dev` or `-Environment prod` |
| One template only (api, video, web, web-cert, billing) | `.\deploy.ps1 -Template <name> -StackName <name> …` (see script parameters) |

There is **no dummy / test stack** in this repo (the old `dummy-stack.yaml` was removed).

### 4. Delete a CloudFormation stack

Use the AWS CLI (replace stack name and region as needed):

```powershell
aws cloudformation delete-stack --stack-name YOUR_STACK --region eu-west-1
aws cloudformation wait stack-delete-complete --stack-name YOUR_STACK --region eu-west-1
```

Or `.\deploy.ps1 -Delete -StackName YOUR_STACK -Template api -Region eu-west-1` (a valid `-Template` is still required so the script can resolve paths before `-Delete` runs).

### 5. Mirrored dev / prod (separate resources per environment)

Each environment has its **own** video bucket, DynamoDB catalog table, Lambda, and API Gateway (no shared data between dev and prod).

| Piece | Dev | Prod |
|--------|-----|------|
| Video (S3) | `StreamMyCourse-Video-dev` | `StreamMyCourse-Video-prod` |
| API + catalog | Stack **`streammycourse-api`** (legacy name; `Environment=dev`) | **`StreamMyCourse-Api-prod`** |
| SPA + ACM edge (us-east-1) | **`StreamMyCourse-EdgeHosting-dev`** (student + teacher S3/CF/R53 + one ACM cert) | **`StreamMyCourse-EdgeHosting-prod`** |
| Legacy split stacks (optional) | `StreamMyCourse-Web-*` / `TeacherWeb-*` / `Cert-*` in older accounts | Same for prod |

**Deploy backend for one environment** (video + API with matching bucket wiring and CORS defaults):

```powershell
cd infrastructure
.\deploy-environment.ps1 -Environment prod
.\deploy-environment.ps1 -Environment dev
```

`deploy-environment.ps1 -Environment dev` targets **`streammycourse-api`** so it does not create a second stack that would collide on the DynamoDB name `StreamMyCourse-Catalog-dev`. To use the name `StreamMyCourse-Api-dev` instead, you must **delete** `streammycourse-api` first, then run `.\deploy-environment.ps1 -Environment dev -NewDevApiStack`.

**Deploy / update SPA** (build + S3 + CloudFront invalidation) — pass the **ApiEndpoint** for *that* environment:

```powershell
# Dev SPA → dev API
.\deploy.ps1 -Template web -StackName StreamMyCourse-Web-dev -Environment dev `
  -DomainName dev.streammycourse.click -HostedZoneId YOUR_ZONE_ID `
  -CertificateArn YOUR_DEV_CERT_ARN `
  -ApiBaseUrl "https://YOUR_DEV_API.execute-api.eu-west-1.amazonaws.com/dev"

# Prod SPA → prod API
.\deploy.ps1 -Template web -StackName StreamMyCourse-Web-prod -Environment prod `
  -DomainName app.streammycourse.click -HostedZoneId YOUR_ZONE_ID `
  -CertificateArn YOUR_PROD_CERT_ARN `
  -ApiBaseUrl "https://YOUR_PROD_API.execute-api.eu-west-1.amazonaws.com/prod"
```

**Teacher dashboard SPA** (separate subdomain; same hosting pattern as student `web`):

- CloudFormation template: **`teacher-web`** (`templates/teacher-web-stack.yaml`). Stack name convention: **`StreamMyCourse-TeacherWeb-{dev|prod}`**.
- **Region:** deploy the stack in **`eu-west-1`** (same as student `web`). **`CertificateArn`** must still be an **ACM certificate in `us-east-1`** (CloudFront requirement); only the cert stack is created in Virginia.
- **S3 bucket name** (in the template): `streammycourse-teacher-{Environment}-{Region}-{AccountId}` so the global bucket name matches the hosting region (avoids cooldown when moving stacks across regions).
- **CI/CD:** On every **full** [`.github/workflows/deploy-backend.yml`](../.github/workflows/deploy-backend.yml) run after integ tests, **`deploy-edge-*`** runs **`edge-hosting-stack.yaml`** as **`StreamMyCourse-EdgeHosting-{env}`** in **`us-east-1`**, then reusable workflows sync assets to the **output buckets** in that region. Migration from legacy three stacks: [`edge-hosting-migration.md`](docs/edge-hosting-migration.md). For **manual-only** hosting, deploy the edge stack once with `deploy.ps1 -Template edge-hosting` (see snippet below) or use legacy `web` / `teacher-web` / `web-cert` templates.

```powershell
# Teacher dev SPA — include teach.* on the ACM cert (or use a cert that covers teach.yourdomain)
cd infrastructure
.\deploy.ps1 -Template teacher-web -StackName StreamMyCourse-TeacherWeb-dev -Environment dev `
  -Region eu-west-1 `
  -DomainName teach.dev.streammycourse.click -HostedZoneId YOUR_ZONE_ID `
  -CertificateArn YOUR_DEV_CERT_ARN `
  -ApiBaseUrl "https://YOUR_DEV_API.execute-api.eu-west-1.amazonaws.com/dev"

# Teacher prod SPA
.\deploy.ps1 -Template teacher-web -StackName StreamMyCourse-TeacherWeb-prod -Environment prod `
  -Region eu-west-1 `
  -DomainName teach.streammycourse.click -HostedZoneId YOUR_ZONE_ID `
  -CertificateArn YOUR_PROD_CERT_ARN `
  -ApiBaseUrl "https://YOUR_PROD_API.execute-api.eu-west-1.amazonaws.com/prod"
```

Add the teacher origins to API **CORS** (`CorsAllowOrigin` CSV) when you go live. Get **`ApiEndpoint`** from CloudFormation → the API stack → Outputs, or:

```powershell
aws cloudformation describe-stacks --stack-name StreamMyCourse-Api-prod --region eu-west-1 --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text
aws cloudformation describe-stacks --stack-name streammycourse-api --region eu-west-1 --query "Stacks[0].Outputs[?OutputKey=='ApiEndpoint'].OutputValue" --output text
```

**Video migration:** Pointing the dev API at `StreamMyCourse-Video-dev` does not copy objects from older buckets; migrate S3 objects separately if needed.

**Lower-level API deploy** (same template as `deploy-environment.ps1` uses internally):

```powershell
.\deploy.ps1 -Template api -StackName streammycourse-api -Environment dev `
  -VideoBucketName YOUR_BUCKET -VideoUrl "https://YOUR_BUCKET.s3.REGION.amazonaws.com" `
  -CorsAllowOrigin "https://dev.streammycourse.click,https://teach.dev.streammycourse.click,http://localhost:5173" -GatewayResponseAllowOrigin '*'
```

Optional **`deploy.ps1`** API parameters: `-VideoUrl`, `-DefaultMp4Url` (passed through to CloudFormation).

## GitHub Actions — automated deploys

**Every push to `main`** runs **integ backend** → **integ tests** → **dev edge** → then **in parallel**: **dev backend + student web + teacher web** and **prod edge** (prod edge does **not** wait for dev Lambda or SPA deploys—only integ tests + dev edge). **Prod** backend and both prod SPAs run only after **prod edge** **and** the full dev column (integ stack, integ tests, dev edge, dev backend, both dev SPAs) succeed. **`cancel-in-progress: false`**: rapid commits **queue**. CloudFormation uses **`--no-fail-on-empty-changeset`**. Lambda code is uploaded as **`catalog-{env}-{gitSha12}.zip`** so **`LambdaCodeS3Key`** changes every commit.

### Secrets (both workflows)

| Secret | What it is | Where to get it |
|--------|------------|-----------------|
| **`AWS_DEPLOY_ROLE_ARN`** | IAM role ARN GitHub assumes via OIDC | Prefer creating/updating the role with [`templates/github-deploy-role-stack.yaml`](templates/github-deploy-role-stack.yaml) (see **GitHub OIDC deploy role** below). Same role for web + backend. Store as a **repository** secret or duplicate under GitHub Environments **`dev`** / **`prod`**. Backend jobs use **`environment: dev`** for OIDC; ensure the ARN is available there or at repo level. |
| **`VITE_API_BASE_URL`** | API base URL **no trailing slash** | Set on GitHub Environment **`dev`** and **`prod`** separately (`streammycourse-api` vs `StreamMyCourse-Api-prod` **ApiEndpoint** outputs). |

### GitHub Environment variables (backend / edge deploy)

Set on GitHub Environments **`dev`** and **`prod`** (values differ per env). Required for **full** [`deploy-backend.yml`](../.github/workflows/deploy-backend.yml) after edge CD is enabled:

| Variable | Purpose |
|----------|---------|
| **`COGNITO_DOMAIN_PREFIX`** | **Required** for full deploy. Globally unique Cognito hosted UI prefix (auth stack); empty fails the workflow. |
| **`ROUTE53_HOSTED_ZONE_ID`** | Route 53 hosted zone for DNS validation (cert) and alias records (web stacks). |
| **`STUDENT_WEB_DOMAIN`** | Full hostname for the student SPA stack (e.g. `dev.streammycourse.click`). Also the default **primary** name on the ACM cert unless **`WEB_CERT_DOMAIN`** is set. |
| **`TEACHER_WEB_DOMAIN`** | Full hostname for the teacher SPA stack (e.g. `teach.dev.streammycourse.click`). |
| **`WEB_CERT_DOMAIN`** | Optional. Primary **`DomainName`** on the ACM certificate when it should differ from **`STUDENT_WEB_DOMAIN`**. |
| **`WEB_CERT_SANS`** | Optional. Comma-separated extra names on the same ACM cert (e.g. teacher hostname) when not covered by the primary name. |

Callback / logout URL variables for Cognito (`STUDENT_COGNITO_*`, `TEACHER_COGNITO_*`) and Google IdP secrets are unchanged; see workflow `env` blocks in `deploy-backend.yml`.

### GitHub OIDC deploy role (CloudFormation bootstrap — not in CI/CD)

**Preferred:** deploy the IAM stack **locally** (admin credentials). This is **not** invoked from GitHub Actions; it bootstraps or updates the OIDC role and inline policies from [`templates/github-deploy-role-stack.yaml`](templates/github-deploy-role-stack.yaml).

```bash
chmod +x scripts/deploy-github-iam-stack.sh
./scripts/deploy-github-iam-stack.sh
```

```powershell
.\scripts\deploy-github-iam-stack.ps1
```

Optional: `GITHUB_IAM_STACK_NAME` overrides the default stack name **`StreamMyCourse-GitHubDeployIam`**.

**Why pass `ExistingGithubOidcProviderArn`?** IAM allows **only one** OIDC provider per issuer URL per account for `https://token.actions.githubusercontent.com`. If that provider already exists (console, CLI, or an earlier bootstrap), CloudFormation **cannot** create another; you get **409 AlreadyExists**. **Deleting this CloudFormation stack does not remove** that IAM OIDC provider—it is not owned by the stack unless the stack successfully created it. So “delete stack and redeploy” alone does **not** clear the conflict; you either **reuse** the existing provider (parameter below) or **delete the IAM OIDC provider** in IAM first (brief disruption to any workflow using it until the stack recreates it—only do that if you intend to move ownership into CloudFormation).

Reuse the existing provider (typical brownfield):

```bash
./scripts/deploy-github-iam-stack.sh --parameter-overrides \
  ExistingGithubOidcProviderArn=arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com
```

After deploy, copy **`GitHubDeployRoleArn`** from stack outputs into **`AWS_DEPLOY_ROLE_ARN`**.

**Parameters:** `GitHubRepository` (default `Ahmed-Wesam/StreamMyCourse`), `RoleName` (default `StreamMyCourseGitHubDeployWeb`), `ExistingGithubOidcProviderArn` (default empty = stack **creates** the GitHub OIDC provider—only works on an account that does **not** already have that URL registered). ARNs inside the template use **`${AWS::AccountId}`** so the same template works across accounts.

**Keep in sync:** The template’s policy statements mirror [`iam-policy-github-deploy-backend.json`](iam-policy-github-deploy-backend.json) and [`iam-policy-github-deploy-web.json`](iam-policy-github-deploy-web.json). When you change permissions, update **both** the YAML template and those JSON files (or drop the JSON files later if you standardize on CFN only). [`iam-trust-github-oidc.json`](iam-trust-github-oidc.json) remains a readable trust-policy reference; the stack encodes the same trust (with `!If` on the federated principal).

**Alternative (policy-only touch):** from the **repository root**, with credentials that can call `iam:PutRolePolicy` on an **existing** role:

```bash
chmod +x scripts/apply-github-deploy-role-policies.sh
./scripts/apply-github-deploy-role-policies.sh
```

```powershell
.\scripts\apply-github-deploy-role-policies.ps1
```

Optional: `GITHUB_DEPLOY_ROLE_NAME` if the role name differs. This path does **not** create the role or OIDC provider and does **not** update the trust policy; use the stack (or `aws iam update-assume-role-policy`) when trust changes.

### `deploy-backend.yml`

[`.github/workflows/deploy-backend.yml`](../.github/workflows/deploy-backend.yml) — **`deploy-edge-dev`** / **`deploy-edge-prod`** run [`scripts/deploy-edge.sh`](../scripts/deploy-edge.sh) (**`StreamMyCourse-EdgeHosting-{env}`** in **us-east-1**). **`deploy-backend-dev`** / **`deploy-backend-prod`** run Cognito (auth) then [`scripts/deploy-backend.sh`](../scripts/deploy-backend.sh). Student and teacher **asset** deploys use the reusable workflows and **`needs`** the corresponding edge job. **Manual dispatch:** **full** or **integ-only**.

### `deploy-web.yml` + `deploy-web-reusable.yml`

[`.github/workflows/deploy-web.yml`](../.github/workflows/deploy-web.yml) orchestrates **dev** then **prod** (same `needs` rule). The reusable workflow [`.github/workflows/deploy-web-reusable.yml`](../.github/workflows/deploy-web-reusable.yml) builds the SPA with **`VITE_API_BASE_URL`** from the target GitHub Environment. **Manual dispatch:** **both** (dev then prod), **dev** only, or **prod** only (standalone, no dev build).

**No extra secrets for site bucket or CloudFront ID** — read from **`StreamMyCourse-EdgeHosting-{env}`** stack outputs (`StudentBucketName` / `StudentDistributionId` for student; teacher outputs for teacher).

## Directory Structure

```
infrastructure/
├── templates/
│   ├── api-stack.yaml        # API Gateway + Lambda + DynamoDB
│   ├── edge-hosting-stack.yaml # Unified ACM + both SPAs (us-east-1); primary CI path
│   ├── github-deploy-role-stack.yaml # GitHub OIDC deploy role + policies (manual bootstrap only)
│   ├── web-stack.yaml        # Legacy student hosting (eu-west-1)
│   ├── teacher-web-stack.yaml # Legacy teacher hosting (eu-west-1)
│   ├── web-cert-stack.yaml   # Legacy ACM-only (us-east-1)
│   └── ...
├── deploy.ps1                 # Single-template deploy (api, web, web-cert, video, …)
├── deploy-environment.ps1     # Video + API for dev or prod (mirrored backends)
└── README.md                  # This file

See also at repo root: [`scripts/deploy-backend.sh`](../scripts/deploy-backend.sh) (Lambda + video + API), [`scripts/deploy-edge.sh`](../scripts/deploy-edge.sh) (cert + student/teacher web CF for CI), [`scripts/deploy-github-iam-stack.sh`](../scripts/deploy-github-iam-stack.sh) / [`.ps1`](../scripts/deploy-github-iam-stack.ps1) (CloudFormation IAM bootstrap for GitHub OIDC), and [`scripts/apply-github-deploy-role-policies.sh`](../scripts/apply-github-deploy-role-policies.sh) / [`.ps1`](../scripts/apply-github-deploy-role-policies.ps1) (optional inline-policy-only sync).
```

## Roadmap / future infra

Post-MVP templates and services are described in [`roadmap.md`](../roadmap.md) (e.g. Cognito, transcoding, scale).

## Cost warning

MVP stacks aim for free-tier–friendly usage. The API stack has no S3 triggers or schedules, which avoids runaway automation.
