# CloudFront signed URLs — green path to prod (agent / operator handoff)

**Branch:** `CloudFormation-migration` — merge to `main` when ready to ship; use this doc for **prod** rollout and CI parity.

## Preconditions

- OIDC deploy role already runs **`./scripts/deploy-backend.sh <env>`** (video stack, then API stack) in `.github/workflows/deploy-backend.yml`.
- Catalog code treats signing as **optional**: full **domain + key pair id + Secrets Manager ARN** enables CloudFront signed URLs; otherwise **S3 presigned GET** fallback.

## Steps (ordered)

### 1. Bootstrap signing keys (per environment; prod when ready)

On a trusted machine with AWS credentials:

```bash
./scripts/deploy-cloudfront-keys-stack.sh prod /path/to/private.pem /path/to/public.pem
```

Save the script output:

- `CLOUDFRONT_PRIVATE_KEY_SECRET_ARN`
- `CLOUDFRONT_PUBLIC_KEY_SSM_PARAMETER_NAME`

Do **not** commit PEMs or paste the private key into GitHub.

### 2. Wire GitHub Environments (so CI does not strip signing)

For **`prod`** (and **`dev`** if you want the same behavior), add **Environment variables** (not the PEM):

| Variable | Purpose |
|----------|---------|
| `CLOUDFRONT_PRIVATE_KEY_SECRET_ARN` | Passed into `deploy-backend.sh` → API stack `CloudFrontPrivateKeySecretArn` |
| `CLOUDFRONT_PUBLIC_KEY_SSM_PARAMETER_NAME` | Passed into `deploy-backend.sh` → video stack `CloudFrontPublicKeySsmParameterName` |

If `.github/workflows/deploy-backend.yml` does **not** yet export these into the **Deploy integ / dev / prod** steps, add an `env:` block on each `./scripts/deploy-backend.sh` step that mirrors local usage.

### 3. Deploy video + API

- **CI:** Push `main` after merge; let **CI** pass, then **Deploy** workflow complete **prod** backend.
- **Local:** `export` the two variables above, then:

```bash
./scripts/deploy-backend.sh prod
```

Order inside the script is fixed: **video** → read CloudFormation outputs → **API**.

### 4. Smoke (prod)

- Play a large MP4: **Range** / seek works via CloudFront.
- Upload or replace a lesson video: **invalidation** yields fresh bytes.
- Optional: near signed URL expiry, confirm lesson player **retries** playback URL once (`LessonPlayerPage`).

### 5. Rollback

Unset the GitHub variables (or unset shell env) and redeploy **API** (or full script): incomplete signing env disables CloudFront signing in the API template; catalog uses **S3 presigned** fallback.

## Agent checklist (repo / IAM)

- After changing `deploy-backend.yml`, keep **YAML parse** parity with `ci.yml` / `scripts/parse_cloudformation_yaml.py`.
- Confirm the GitHub OIDC deploy role (see `infrastructure/iam-policy-github-deploy-backend.json` and/or `github-deploy-role-stack`) allows **`secretsmanager:GetSecretValue`** on the signing secret and **`lambda:InvokeFunction`** on the video stack invalidation Lambda if the API template grants those to the catalog Lambda.

## What stays out of routine CI

- **`cloudfront-keys-stack`**: bootstrap / rare template changes only (see `infrastructure/templates/cloudfront-keys-stack.yaml` + script header). CI should **parse** the template, not redeploy this stack on every push unless you harden the template for safe updates.
