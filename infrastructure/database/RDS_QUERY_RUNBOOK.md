# RDS query and catalog wipe (operator Lambda)

**Purpose:** In-VPC Lambda `StreamMyCourse-RdsQuery-<env>` for **read-only SQL**, **gated mutating SQL**, and **catalog wipe** (`TRUNCATE enrollments, lessons, courses, users RESTART IDENTITY CASCADE`). There is **no HTTP endpoint**—invoke only with `aws lambda invoke` and credentials that have `lambda:InvokeFunction` on this function.

**Region:** `eu-west-1` (unless your stacks differ).

## Security model

- **Not customer-facing:** no API Gateway, no Lambda function URL, no route on the public catalog API.
- **AWS IAM:** grant operators **only** `lambda:InvokeFunction` on `arn:aws:lambda:<region>:<account>:function:StreamMyCourse-RdsQuery-<env>`. Avoid policies with `Resource: "*"` for Lambda invoke.
- **Payload gates:** `confirm` must match the stack environment. **`wipe_catalog`** requires template/env **`ALLOW_CATALOG_WIPE=true`**. Mutating **`sql`** requires **`allow_mutating_sql: true`** in the payload **and** **`ALLOW_MUTATING_SQL=true`** on the function. **`wipe_catalog` and `sql` are mutually exclusive.**
- **Read SQL guard:** The read path rejects common **DML/DDL** substrings anywhere in the statement (e.g. `DELETE FROM`, `UPDATE … SET`, `SELECT … INTO`, `WITH` bodies that contain those patterns). This is a **heuristic**, not a SQL parser—rare false positives are possible; use the mutating path for intentional DDL/DML.

## Deploy

From repo root (Git Bash / WSL; same packaging pattern as other RDS helper Lambdas):

```bash
./scripts/deploy-rds-query-stack.sh dev
```

Optional environment variables for the deploy script (defaults `false`):

```bash
ALLOW_CATALOG_WIPE=true ALLOW_MUTATING_SQL=false ./scripts/deploy-rds-query-stack.sh prod
```

This uploads a zip to the artifacts bucket and deploys **`StreamMyCourse-RdsQuery-<env>`**, importing subnet, Lambda security group, and DB secret from **`StreamMyCourse-Rds-<env>`**.

After maintenance, redeploy with **`ALLOW_CATALOG_WIPE=false`** (omit env vars) so the function rejects wipe invocations again.

## Invoke (PowerShell-safe payload file)

**Read example** (`payload.json`):

```json
{"confirm":"dev","sql":"SELECT COUNT(*) FROM courses"}
```

```bash
aws lambda invoke --function-name StreamMyCourse-RdsQuery-dev \
  --cli-binary-format raw-in-base64-out \
  --payload fileb://payload.json \
  /tmp/rds-query-dev-out.json --region eu-west-1
cat /tmp/rds-query-dev-out.json
```

**Catalog wipe** (only after deploy with `AllowCatalogWipe=true` / `ALLOW_CATALOG_WIPE=true`):

```json
{"confirm":"dev","wipe_catalog":true}
```

Response includes `counts_before` and `counts_after` per table when `ok` is true.

**Mutating SQL** (only with `AllowMutatingSql=true` and payload flag):

```json
{"confirm":"dev","sql":"DELETE FROM enrollments WHERE false","allow_mutating_sql":true}
```

## Legacy S3 key layout refactor (historical procedure)

The old standalone wipe Lambda and **`RDS_WIPE_RUNBOOK`** are removed; use this runbook instead.

**When:** Before deploying the catalog Lambda that uses `{courseId}/lessons/...` S3 keys, wipe **dev** then **prod** so old `uploads/...` rows and objects do not break playback.

### 1. Prod RDS snapshot (mandatory before prod TRUNCATE)

```bash
aws rds create-db-snapshot \
  --db-instance-identifier streammycourse-prod \
  --db-snapshot-identifier "streammycourse-prod-pre-s3-refactor-$(date +%Y%m%d)" \
  --region eu-west-1
aws rds wait db-snapshot-available \
  --db-snapshot-identifier "streammycourse-prod-pre-s3-refactor-$(date +%Y%m%d)" \
  --region eu-west-1
```

Record the snapshot identifier in your ops log.

### 2. Build and deploy the query stack with wipe enabled

```bash
ALLOW_CATALOG_WIPE=true ./scripts/deploy-rds-query-stack.sh dev
ALLOW_CATALOG_WIPE=true ./scripts/deploy-rds-query-stack.sh prod
```

### 3. Empty the video bucket, invoke wipe, lock down again

**Dev**

```bash
BUCKET=$(aws cloudformation describe-stacks --stack-name StreamMyCourse-Video-dev \
  --query "Stacks[0].Outputs[?OutputKey=='BucketName'].OutputValue" --output text --region eu-west-1)
aws s3 rm "s3://${BUCKET}/" --recursive --region eu-west-1

aws lambda invoke --function-name StreamMyCourse-RdsQuery-dev \
  --cli-binary-format raw-in-base64-out \
  --payload fileb://wipe-payload.json \
  /tmp/rds-query-dev-out.json --region eu-west-1
cat /tmp/rds-query-dev-out.json
```

Where `wipe-payload.json` contains `{"confirm":"dev","wipe_catalog":true}`.

Redeploy **without** `ALLOW_CATALOG_WIPE` when finished.

**Prod** (after snapshot in §1): same pattern with `prod` and `StreamMyCourse-Video-prod`.

### 4. Deploy order after wipe

1. Empty S3 → TRUNCATE RDS → **then** deploy catalog + API stack (IAM `bucket/*` + new presign logic).

Do **not** deploy the new Lambda before TRUNCATE, or rows still holding `uploads/...` keys will fail `presign_get` until wiped.

## Retiring old wipe stacks

If **`StreamMyCourse-RdsWipe-<env>`** still exists in AWS from earlier work, delete it after you rely on **`StreamMyCourse-RdsQuery-<env>`**:

```bash
aws cloudformation delete-stack --stack-name StreamMyCourse-RdsWipe-dev --region eu-west-1
```
