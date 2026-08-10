# Prod shutdown and restore runbook

**Scope:** Pause or tear down **prod** CloudFormation stacks to reduce AWS spend while retaining restorable data (S3 buckets with `Retain`, RDS final snapshot). Bring prod back with the pause manifest and restore scripts, or via a greenfield GitHub **Deploy** dispatch when retained buckets are gone.

**Scripts (source of truth):**

| Script | Role |
|--------|------|
| [`scripts/export-pause-manifest.sh`](../../scripts/export-pause-manifest.sh) | Export restore metadata from live stack outputs (no secret values) |
| [`scripts/teardown-prod.sh`](../../scripts/teardown-prod.sh) | Ordered stack deletes + optional manifest export |
| [`scripts/teardown-prod.ps1`](../../scripts/teardown-prod.ps1) | Windows wrapper → Git Bash / WSL |
| [`scripts/restore-prod.sh`](../../scripts/restore-prod.sh) | Import retained buckets, redeploy stacks from manifest + RDS snapshot |
| [`scripts/sync-rds-secret-after-restore.sh`](../../scripts/sync-rds-secret-after-restore.sh) | Align RDS master password with Secrets Manager after snapshot restore |
| [`scripts/lib/prod_pause_constants.sh`](../../scripts/lib/prod_pause_constants.sh) | Shared teardown stack order and manifest key list |

Stack order and manifest keys are also enforced by [`tests/unit/test_prod_pause_scripts.py`](../../tests/unit/test_prod_pause_scripts.py).

---

## 1. Overview / when to use

Use this runbook when you need to **stop prod AWS spend** for an extended period (account pause, cost control, migration window) while keeping a path to restore course media, SPA assets, and PostgreSQL data.

**What shutdown does**

- Deletes prod CloudFormation stacks in dependency-safe order (see §3).
- **Retains** S3 buckets defined with `DeletionPolicy: Retain` in [`edge-hosting-stack.yaml`](../templates/edge-hosting-stack.yaml) (student + teacher site buckets) and [`video-stack.yaml`](../templates/video-stack.yaml) (video/uploads bucket).
- **Snapshots** RDS on `StreamMyCourse-Rds-prod` stack delete (`DeletionPolicy: Snapshot` on the DB instance in [`rds-stack.yaml`](../templates/rds-stack.yaml)).
- Does **not** export or store secrets; the pause manifest holds infrastructure IDs and GitHub Environment **names** only.

**What restore does**

- **Retained-bucket path:** [`restore-prod.sh`](../../scripts/restore-prod.sh) CloudFormation-imports existing buckets, redeploys edge/RDS/auth/backend, syncs RDS credentials, applies schema, then prints follow-up steps (GitHub secrets + integration tests + SPA deploy).
- **Greenfield path:** If retained buckets were deleted, `restore-prod.sh` cannot import them — use GitHub **Deploy** `workflow_dispatch` (§6) to create fresh stacks (data in deleted buckets is not recovered by these scripts).

**When not to use**

- Dev/test stacks — use other tooling (e.g. [`remove-dev-stack-prod-only.yml`](../../.github/workflows/remove-dev-stack-prod-only.yml)).
- Partial stack edits — use normal deploy scripts / CI instead of full teardown.

---

## 2. Pre-flight checklist

Complete **before** any mutating teardown step.

### Disable automated prod deploys

1. In GitHub: **Actions** → workflow **Deploy** ([`deploy-backend.yml`](../../.github/workflows/deploy-backend.yml)) → **⋯** → **Disable workflow** (or restrict who can run it).
2. Confirm no **Deploy** run is in progress.
3. Avoid pushes to `main` that would trigger deploy after re-enabling CI gate — shutdown is manual-only until restore completes.

### Confirm AWS account and credentials

```bash
aws sts get-caller-identity --query Account --output text
```

Expect the **prod** account ID. Teardown and restore both prompt you to re-type this account ID when using `--confirm`.

### Operator tooling

- **AWS CLI** configured for prod.
- **bash** (Git Bash / WSL on Windows) for all scripts except the PowerShell teardown wrapper.
- **jq** — required by `restore-prod.sh` for manifest parsing.
- **python3** — used by export and sync scripts.

### Record GitHub Environment prod configuration

Export does not copy secret values. Ensure you can restore these names (also listed in manifest `github_env_checklist`):

- `AWS_DEPLOY_ROLE_ARN`
- `COGNITO_DOMAIN_PREFIX`
- `ROUTE53_HOSTED_ZONE_ID`
- `STUDENT_WEB_DOMAIN`
- `TEACHER_WEB_DOMAIN`
- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `COGNITO_RDS_VERIFY_*` (integration / verify-rds credentials)

Store existing values in your password manager before teardown.

---

## 3. Shutdown procedure

### Step A — Export pause manifest

Run **before** stack deletes so stack outputs are still available. Default output `pause-manifest.json` is **gitignored** — copy it off-repo immediately.

```bash
./scripts/export-pause-manifest.sh
# or explicit path:
./scripts/export-pause-manifest.sh --out /secure/path/pause-manifest-prod.json
```

Manifest fields (see [`PAUSE_MANIFEST_JSON_KEYS`](../../scripts/lib/prod_pause_constants.sh)): `aws_account_id`, `regions`, bucket names, API/Cognito/RDS host identifiers, `rds_snapshot_identifier` (empty until §4), `github_env_checklist`.

You can combine export with teardown:

```bash
./scripts/teardown-prod.sh --manifest-out /secure/path/pause-manifest-prod.json --confirm
```

(`--manifest-out` without `--confirm` is refused unless `--dry-run`.)

### Step B — Preview teardown (dry-run)

**Bash:**

```bash
./scripts/teardown-prod.sh --dry-run
```

**PowerShell:**

```powershell
.\scripts\teardown-prod.ps1 --dry-run
```

Review printed steps: WAF cleanup, primary stack list, legacy stack list. No AWS mutations.

### Step C — Execute teardown

**Bash:**

```bash
./scripts/teardown-prod.sh --confirm
# if some stacks were already removed:
./scripts/teardown-prod.sh --confirm --skip-missing
# export + teardown in one run:
./scripts/teardown-prod.sh --confirm --manifest-out /secure/path/pause-manifest-prod.json
```

**PowerShell:**

```powershell
.\scripts\teardown-prod.ps1 --confirm
.\scripts\teardown-prod.ps1 --confirm --skip-missing
.\scripts\teardown-prod.ps1 --confirm --manifest-out C:\secure\pause-manifest-prod.json
```

When `--confirm` is set (and not `--dry-run`), the script prompts:

```text
Type AWS account ID (<account-id>) to confirm prod teardown:
```

### Teardown order (implemented)

**Step 0 — WAF** ([`scripts/delete-waf-stacks.sh`](../../scripts/delete-waf-stacks.sh)):

- `StreamMyCourse-ApiWaf-prod` (eu-west-1)
- `StreamMyCourse-EdgeWaf-prod` (us-east-1)

**Primary stacks** ([`TEARDOWN_STACKS`](../../scripts/lib/prod_pause_constants.sh)):

| Order | Stack | Region |
|------:|-------|--------|
| 1 | StreamMyCourse-Api-prod | eu-west-1 |
| 2 | StreamMyCourse-Auth-prod | eu-west-1 |
| 3 | StreamMyCourse-VideoProviderEdge-prod | eu-west-1 |
| 4 | StreamMyCourse-Payments-prod | eu-west-1 |
| 5 | StreamMyCourse-MediaCleanup-prod | eu-west-1 |
| 6 | StreamMyCourse-RdsQuery-prod | eu-west-1 |
| 7 | StreamMyCourse-Rds-prod | eu-west-1 |
| 8 | StreamMyCourse-Video-prod | eu-west-1 |
| 9 | StreamMyCourse-EdgeHosting-prod | us-east-1 |
| 10 | StreamMyCourse-ArtifactJanitor-prod | eu-west-1 |

Before deleting **StreamMyCourse-Rds-prod**, teardown disables **deletion protection** on RDS instance `streammycourse-prod` and waits until the instance is `available`.

**Legacy stacks** (deleted if present):

- `StreamMyCourse-Web-prod` (us-east-1)
- `StreamMyCourse-TeacherWeb-prod` (us-east-1)
- `StreamMyCourse-Cert-prod` (us-east-1)

Each stack delete waits for `stack-delete-complete`.

---

## 4. Post-delete cleanup

### Retained resources (do not delete)

| Resource | Why |
|----------|-----|
| **Video S3 bucket** (`video_bucket_name` in manifest) | `DeletionPolicy: Retain` on `VideoBucket` |
| **Student site bucket** (`student_bucket_name`) | Retain on `SiteBucket` |
| **Teacher site bucket** (`teacher_bucket_name`) | Retain on `TeacherSiteBucket` |
| **RDS snapshot(s)** | Created on `StreamMyCourse-Rds-prod` delete; required for DB restore |
| **Pause manifest** (off-repo copy) | Restore input; never commit `pause-manifest.json` |
| **GitHub Environment `prod` vars/secrets** | Required for edge/auth deploy and CI |

### Record RDS snapshot ID

After `StreamMyCourse-Rds-prod` delete, find the **final snapshot** (stack delete or any manual snapshot you took pre-teardown) and set it in the manifest:

```bash
aws rds describe-db-snapshots \
  --region eu-west-1 \
  --query "DBSnapshots[?contains(DBSnapshotIdentifier, 'streammycourse-prod')].DBSnapshotIdentifier" \
  --output text
```

Edit the saved manifest JSON:

```json
"rds_snapshot_identifier": "rds:streammycourse-prod-2026-08-05-..."
```

`restore-prod.sh` **requires** a non-empty `rds_snapshot_identifier`.

### Optional housekeeping (outside scripts)

- **Artifact bucket** `streammycourse-artifacts-<account>-eu-west-1` may still exist; safe to keep for restore uploads.
- **Secrets Manager** secret `streammycourse/prod/rds-credentials` may outlive the RDS instance; restore reuses it via `deploy-rds-stack.sh` + `sync-rds-secret-after-restore.sh`.
- **Do not** delete retained buckets or RDS snapshots unless you accept **permanent** loss of that data tier.

### Re-enable deploy workflow

Leave **Deploy** disabled until restore verification (§7) or until you intentionally start greenfield deploy (§6).

---

## 5. Restore procedure (retained buckets + snapshot)

Use when the three manifest bucket names still exist in AWS and you have a valid `rds_snapshot_identifier`.

### Required environment variables

**Edge** (import + `deploy-edge.sh`):

| Variable | Required |
|----------|----------|
| `ROUTE53_HOSTED_ZONE_ID` | Yes |
| `STUDENT_WEB_DOMAIN` | Yes |
| `TEACHER_WEB_DOMAIN` | Yes |
| `WEB_CERT_DOMAIN` | No (defaults to `STUDENT_WEB_DOMAIN`) |
| `WEB_CERT_SANS` | No |
| `EDGE_ATTACH_CF_ALIASES` | No (default `true`) |

**Auth** (`auth-stack.yaml` deploy inside restore):

| Variable | Required |
|----------|----------|
| `COGNITO_DOMAIN_PREFIX` | Yes |
| `GOOGLE_OAUTH_CLIENT_ID` | Yes |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Yes |
| `STUDENT_COGNITO_CALLBACK_URLS` / `STUDENT_COGNITO_LOGOUT_URLS` | No |
| `TEACHER_COGNITO_CALLBACK_URLS` / `TEACHER_COGNITO_LOGOUT_URLS` | No |

**Backend:** `VIDEO_PROVIDER` optional (default `s3` in restore script).

Example (bash):

```bash
export ROUTE53_HOSTED_ZONE_ID=Z0123456789ABC
export STUDENT_WEB_DOMAIN=researchspectrum.org
export TEACHER_WEB_DOMAIN=teach.researchspectrum.org
export COGNITO_DOMAIN_PREFIX=streammycourse-prod
export GOOGLE_OAUTH_CLIENT_ID='...'
export GOOGLE_OAUTH_CLIENT_SECRET='...'
```

### Preview restore

```bash
./scripts/restore-prod.sh --manifest /secure/path/pause-manifest-prod.json --dry-run
```

### Execute restore

```bash
./scripts/restore-prod.sh --manifest /secure/path/pause-manifest-prod.json --confirm
```

Confirms manifest `aws_account_id` matches current CLI account, then prompts for account ID again.

**Restore steps (in order):**

1. **Import retained S3** — CloudFormation import for `StreamMyCourse-EdgeHosting-prod` (us-east-1) and `StreamMyCourse-Video-prod` (eu-west-1); skips if stack already exists.
2. **Deploy edge** — `./scripts/deploy-edge.sh prod`
3. **Deploy RDS from snapshot** — `RESTORE_DB_SNAPSHOT_IDENTIFIER=<manifest value> ./scripts/deploy-rds-stack.sh prod`
4. **Sync RDS secret** — `./scripts/sync-rds-secret-after-restore.sh prod`
5. **Apply schema** — invoke schema-applier Lambda from RDS stack output `SchemaApplierFunctionName`
6. **Deploy auth** — Cognito stack with user-profile sync Lambda artifact upload
7. **Deploy backend** — `./scripts/deploy-backend.sh prod` (media cleanup, payments, API, etc.)

### Post-restore script output

`restore-prod.sh` prints:

1. Sync GitHub secrets: `.\scripts\set-github-auth-secrets-from-stack.ps1 -Environment prod`
2. Integration tests: `.\scripts\run-integration-tests.ps1` or `./scripts/run-local-integration-tests.sh`
3. Deploy SPAs via GitHub Actions (push `main` or deploy workflows after **Deploy** is re-enabled)

### RDS credential sync (standalone)

If you deploy RDS from snapshot outside `restore-prod.sh`, run:

```bash
./scripts/sync-rds-secret-after-restore.sh prod
```

Snapshot restores keep the **snapshot’s** master password; the stack’s Secrets Manager secret may differ. This script sets the instance password from `streammycourse/prod/rds-credentials` and waits until `streammycourse-prod` is available.

---

## 6. Greenfield restore via GitHub `workflow_dispatch`

Use when **retained S3 buckets were deleted** (or never existed). `restore-prod.sh` checks bucket existence and **exits** if import targets are missing.

1. Ensure prod stacks from teardown are gone (or use `--skip-missing` during teardown).
2. Restore GitHub **Environment `prod`** vars/secrets (Route53, domains, Google OAuth, deploy role ARN).
3. Re-enable workflow **Deploy** ([`deploy-backend.yml`](../../.github/workflows/deploy-backend.yml)).
4. **Actions** → **Deploy** → **Run workflow** → branch `main` → **Run workflow**.

The dispatch runs the full prod pipeline (edge, RDS, schema apply, backend, integration HTTP tests, verify RDS, student + teacher SPA deploys) without waiting for CI on `main`.

**Data implications**

- **New S3 buckets** — empty; previous bucket objects are not restored by this workflow.
- **RDS** — CI `deploy-rds-prod` deploys a **fresh** instance (no `DbSnapshotIdentifier` in the workflow). To recover PostgreSQL data when a snapshot still exists, run locally **before or instead of** relying on that job:

  ```bash
  export RESTORE_DB_SNAPSHOT_IDENTIFIER='rds:streammycourse-prod-...'
  ./scripts/deploy-rds-stack.sh prod
  ./scripts/sync-rds-secret-after-restore.sh prod
  ```

  Then align CI/backend deploy with the restored DB, or run `restore-prod.sh` steps 5–7 manually after edge/video/RDS are in place.

---

## 7. Verification

### Integration tests

From repo root with prod credentials in `.env.local` (`LOCAL_COGNITO_PASSWORD` per [AGENTS.md](../../AGENTS.md)):

```powershell
.\scripts\run-integration-tests.ps1
```

```bash
./scripts/run-local-integration-tests.sh
```

Confirm HTTPS tests pass against prod API and Cognito.

### GitHub auth secrets

After new Cognito stack:

```powershell
.\scripts\set-github-auth-secrets-from-stack.ps1 -Environment prod
```

Rebuild SPAs if pool/client IDs changed (Deploy workflow or reusable web deploy jobs).

### Smoke checks

- Student and teacher URLs load over HTTPS.
- Google sign-in via Cognito Hosted UI.
- API health/catalog endpoints respond.
- Video playback from retained bucket (retained-bucket restore path).

### Billing

- **AWS Billing** / Cost Explorer: confirm tear-down removed daily spend from deleted stacks (Lambda, API Gateway, CloudFront, RDS compute, etc.).
- Expect minimal ongoing cost for **retained S3**, **RDS snapshot storage**, and any orphaned secrets/logs until fully cleaned up.

---

## 8. Known limitations

| Limitation | Detail |
|------------|--------|
| **Cognito users** | Teardown deletes `StreamMyCourse-Auth-prod`. Restore creates a **new** user pool. Manifest `user_pool_id` and client IDs are **historical**; users must sign in again via Google on the new pool. |
| **CFN import one-time** | Each retained bucket can be imported into a stack once. If `StreamMyCourse-EdgeHosting-prod` or `StreamMyCourse-Video-prod` already exists, import is skipped — do not delete only the stack while keeping buckets unless you plan a manual re-import. |
| **RDS credential sync** | Snapshot password ≠ Secrets Manager until `sync-rds-secret-after-restore.sh` runs. Lambda/schema applier failures after restore often mean this step was skipped. |
| **Manifest snapshot field** | Export leaves `rds_snapshot_identifier` empty; operator must fill after RDS delete (§4). |
| **No secret export** | Pause manifest never includes passwords, OAuth secrets, or JWTs. |
| **DynamoDB catalog** | Deleted with API stack; restore redeploys empty catalog unless RDS snapshot contained app data only (catalog is DynamoDB, not RDS). |
| **Windows** | `teardown-prod.ps1` delegates to bash; Git Bash or WSL required. `restore-prod.sh` is bash-only. |
| **Deletion protection** | Teardown disables RDS deletion protection before RDS stack delete; do not run teardown against unintended accounts. |

---

## 9. Example CloudFormation import JSON

Logical IDs and structure match [`restore-prod.sh`](../../scripts/restore-prod.sh). Replace bucket names with values from your pause manifest.

### Edge hosting (`StreamMyCourse-EdgeHosting-prod`, us-east-1)

Template: `infrastructure/templates/edge-hosting-stack.yaml`

```json
[
  {
    "ResourceType": "AWS::S3::Bucket",
    "LogicalResourceId": "SiteBucket",
    "ResourceIdentifier": {
      "BucketName": "<student_bucket_name>"
    }
  },
  {
    "ResourceType": "AWS::S3::Bucket",
    "LogicalResourceId": "TeacherSiteBucket",
    "ResourceIdentifier": {
      "BucketName": "<teacher_bucket_name>"
    }
  }
]
```

Parameter overrides used by restore (non-exhaustive): `Environment=prod`, `HostedZoneId`, `CertPrimaryDomain`, `StudentDomainName`, `TeacherDomainName`, `PriceClass=PriceClass_100`, `AttachCloudFrontAliases`.

### Video (`StreamMyCourse-Video-prod`, eu-west-1)

Template: `infrastructure/templates/video-stack.yaml`

```json
[
  {
    "ResourceType": "AWS::S3::Bucket",
    "LogicalResourceId": "VideoBucket",
    "ResourceIdentifier": {
      "BucketName": "<video_bucket_name>"
    }
  }
]
```

Restore also uploads a CloudFront invalidation Lambda zip to `streammycourse-artifacts-<account>-eu-west-1` and passes `InvalidationLambdaCodeS3Bucket`, `InvalidationLambdaCodeS3Key`, and `CorsAllowedOrigins` on import.

---

## Related docs

- [Admin auth runbook](./admin-auth-runbook.md) — Cognito / Google OAuth expectations
- [AGENTS.md](../../AGENTS.md) — CI, integration tests, deploy entry points
- [Edge hosting migration](./edge-hosting-migration.md) — unified edge stack context
