# Integration tests

HTTPS-driven tests that exercise the deployed `integ` backend (API Gateway + Lambda + DynamoDB + S3) end-to-end.

## What gets tested

Every test creates state through the public API, asserts on the API responses, and deletes its state at teardown. Lesson and course cleanup happens via `DELETE /courses/{id}` (course delete cascades to lessons). S3 objects from upload-url tests are removed via boto3 in a session-end safety net (warn-only, never fails CI).

See [`integration_testing_strategy_e5a09a54.plan.md`](../../.cursor/plans/integration_testing_strategy_e5a09a54.plan.md) for the full plan.

## Running locally

The tests need a deployed `integ` stack (`StreamMyCourse-Api-integ` + `StreamMyCourse-Video-integ`). Deploy it once with:

```powershell
# from repo root
.\infrastructure\deploy-environment.ps1 -Environment integ
```

or, on bash / WSL / CI:

```bash
./scripts/deploy-backend.sh integ
```

Then export the resource locations and run pytest:

```bash
export INTEG_API_BASE_URL="$(aws cloudformation describe-stacks \
  --stack-name StreamMyCourse-Api-integ \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)"
export INTEG_TABLE_NAME=StreamMyCourse-Catalog-integ
export INTEG_VIDEO_BUCKET="$(aws cloudformation describe-stacks \
  --stack-name StreamMyCourse-Video-integ \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)"
export INTEG_REGION=eu-west-1

# Optional: JWT from your Cognito app client (hosted UI sign-in → copy id/access token).
# Enables `test_users_me_with_bearer_returns_profile_when_enforced` when the pool authorizer is on.
# export INTEG_COGNITO_JWT='eyJ...'

pip install -r tests/integration/requirements.txt
python -m pytest tests/integration -q
```

PowerShell equivalent:

```powershell
$env:INTEG_API_BASE_URL = (aws cloudformation describe-stacks --stack-name StreamMyCourse-Api-integ --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text)
$env:INTEG_TABLE_NAME = 'StreamMyCourse-Catalog-integ'
$env:INTEG_VIDEO_BUCKET = (aws cloudformation describe-stacks --stack-name StreamMyCourse-Video-integ --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
$env:INTEG_REGION = 'eu-west-1'

pip install -r tests\integration\requirements.txt
python -m pytest tests\integration -q
```

Or use the helper script (deploys first by default, then runs tests):

```powershell
.\scripts\run-integ.ps1
```

## AWS permissions for local runs

Your AWS profile needs:

- `cloudformation:DescribeStacks` on `StreamMyCourse-Api-integ` and `StreamMyCourse-Video-integ` (to read endpoint + bucket name)
- `dynamodb:Scan`, `dynamodb:Query`, `dynamodb:DeleteItem`, `dynamodb:BatchWriteItem` on the integ table (safety-net cleanup)
- `s3:ListBucket`, `s3:DeleteObject` on the integ video bucket (safety-net cleanup)

The HTTP test calls themselves do not need AWS credentials -- they go through API Gateway. AWS credentials are only used by the safety-net cleanup at session end.

## Test layout

```
tests/integration/
  conftest.py            -- fixtures (api, http_client, course_factory, lesson_factory) + session safety net
  helpers/
    api.py               -- ApiClient wrapping httpx.Client with one method per route
    factories.py         -- course/lesson factory builders + TEST_TITLE_PREFIX
    cleanup.py           -- boto3-based safety-net cleanup utilities
  test_auth_gateway.py   -- `/users/me`, CORS preflight, POST /courses vs Cognito (optional JWT)
  test_*.py              -- one module per scenario group (S1-S5 in the plan)
```

## Smoke testing the RDS PostgreSQL migration

When the Lambda is deployed with `USE_RDS=true`, the existing integration suite
doubles as the RDS smoke test -- every scenario round-trips through the
PostgreSQL adapter instead of DynamoDB. The public API contract is unchanged,
so no test source edits are required.

**Local preflight (optional):** From the repo root, [`scripts/deploy-rds-stack.sh`](../../scripts/deploy-rds-stack.sh) mirrors the CI packaging + `aws cloudformation deploy` + `aws rds wait` for **`dev`**, **`integ`**, or **`prod`** (set `AWS_REGION`, e.g. `eu-west-1`). On Windows, use **Git Bash**; if `zip` is missing, the script falls back to Python to build the Lambda zip. **`SKIP_SCHEMA_APPLIER=1`** deploys VPC + RDS only (empty schema-applier S3 parameters).

**Dev CI/CD:** On pushes to `main`, [`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml) builds a small zip under `infrastructure/lambda/rds_schema_apply/`, uploads it to the artifacts bucket, deploys [`rds-stack.yaml`](../../infrastructure/templates/rds-stack.yaml) with `SchemaApplierCodeS3Bucket` / `SchemaApplierCodeS3Key`, then **`apply-schema-dev`** invokes **`StreamMyCourse-RdsSchemaApplier-dev`** so schema DDL runs from inside the VPC (no `psql` from GitHub-hosted runners to private RDS).

The **Verify dev RDS** and **Verify prod RDS** jobs both call [`.github/workflows/verify-rds-reusable.yml`](../../.github/workflows/verify-rds-reusable.yml): one shared procedure (resolve stacks from **inputs**, mint JWT or use fallback, run `test_rds_path.py`). The workflow passes **`vars.AWS_DEPLOY_ROLE_ARN`** into the reusable workflow (`workflow_call` does not allow `secrets`/`env` in `with:`); set a **repository Actions variable** `AWS_DEPLOY_ROLE_ARN` to the IAM role ARN from [`github-deploy-role-stack.yaml`](../../infrastructure/templates/github-deploy-role-stack.yaml) output **`GitHubDeployRoleArn`** (same value as used on **dev**/**prod** environments for other Deploy jobs). **`deploy-backend.yml` only passes `github_environment` (`dev` | `prod`) and stack names** — it does not thread secrets between environments. The reusable job sets **`environment: ${{ inputs.github_environment }}`**, so GitHub resolves credentials **only** from that environment’s store.

**GitHub Environment keys (same names on dev and prod; values differ per environment):**

- **Secret** `COGNITO_RDS_VERIFY_TEST_PASSWORD` — permanent password for the dedicated teacher test user `ci-rds-verify@noreply.local` in that environment’s Cognito pool.
- **Variable** `COGNITO_RDS_VERIFY_TEST_USERNAME` — optional; workflow defaults to `ci-rds-verify@noreply.local` if unset.
- **Secret** `COGNITO_RDS_VERIFY_JWT` — optional static token if minting fails (Actions emits a `::warning::` when used after a mint failure).

The reusable workflow mints an **IdToken** with `aws cognito-idp admin-initiate-auth` (`ADMIN_USER_PASSWORD_AUTH` against the **teacher** client from the **auth stack name passed as input** — `StreamMyCourse-Auth-dev` vs `StreamMyCourse-Auth-prod` — only in `deploy-backend.yml`). It sets runtime **`INTEG_COGNITO_JWT`** for pytest; `conftest.py` sends `Authorization: Bearer …`. (`INTEG_COGNITO_JWT` is not a GitHub secret name.)

**Cutover / cleanup:** Add the unified keys on **dev** and **prod** before merging (or expect one failed Verify until they exist). GitHub never returns secret values after set — copy from your vault before deleting old names. With [GitHub CLI](https://cli.github.com/) (Windows builds may lack `--body-file`; pipe the password in instead of `-b` when it contains shell metacharacters):

```powershell
# dev environment
gh secret set COGNITO_RDS_VERIFY_TEST_PASSWORD -e dev -b"<password>"
gh secret set COGNITO_RDS_VERIFY_JWT -e dev -b"<optional-static-jwt>"
gh variable set COGNITO_RDS_VERIFY_TEST_USERNAME -e dev -b"ci-rds-verify@noreply.local"

# prod environment
gh secret set COGNITO_RDS_VERIFY_TEST_PASSWORD -e prod -b"<password>"
gh secret set COGNITO_RDS_VERIFY_JWT -e prod -b"<optional>"
gh variable set COGNITO_RDS_VERIFY_TEST_USERNAME -e prod -b"ci-rds-verify@noreply.local"
```

```powershell
# After green Deploy — remove superseded suffixed names (skip missing)
gh secret delete COGNITO_RDS_VERIFY_DEV_TEST_PASSWORD -e dev 2>$null
gh secret delete COGNITO_RDS_VERIFY_DEV_JWT -e dev 2>$null
gh variable delete COGNITO_RDS_VERIFY_DEV_TEST_USERNAME -e dev 2>$null
gh secret delete COGNITO_RDS_VERIFY_PROD_TEST_PASSWORD -e prod 2>$null
gh secret delete COGNITO_RDS_VERIFY_PROD_JWT -e prod 2>$null
gh variable delete COGNITO_RDS_VERIFY_PROD_TEST_USERNAME -e prod 2>$null

# Legacy integ-style keys
gh secret delete INTEG_DEV_COGNITO_TEST_PASSWORD -e dev 2>$null
gh secret delete INTEG_DEV_COGNITO_JWT -e dev 2>$null
gh variable delete INTEG_DEV_COGNITO_TEST_USERNAME -e dev 2>$null
gh secret delete INTEG_PROD_COGNITO_TEST_PASSWORD -e prod 2>$null
gh secret delete INTEG_PROD_COGNITO_JWT -e prod 2>$null
gh variable delete INTEG_PROD_COGNITO_TEST_USERNAME -e prod 2>$null
```

**Bootstrap the CI user once** (operator workstation with admin Cognito access):

```bash
CI_RDS_VERIFY_PASSWORD='choose-a-strong-password' ./scripts/ensure-ci-rds-verify-cognito-user.sh
```

For **dev**, set **`COGNITO_RDS_VERIFY_TEST_PASSWORD`** on the **dev** GitHub Environment to the same value. For **prod**, run with `CI_RDS_VERIFY_AUTH_STACK=StreamMyCourse-Auth-prod` and set **`COGNITO_RDS_VERIFY_TEST_PASSWORD`** on the **prod** environment.

For local runs of the same tests, mint a token or `export INTEG_COGNITO_JWT='eyJ…'` (see optional JWT note above).

Recommended cutover verification sequence:

```bash
# 1. Deploy the RDS stack (one-time per environment).
aws cloudformation deploy \
  --template-file infrastructure/templates/rds-stack.yaml \
  --stack-name StreamMyCourse-Rds-integ \
  --parameter-overrides "Environment=integ" \
  --capabilities CAPABILITY_IAM \
  --region eu-west-1

# 2. Apply the schema (from an operator workstation via SSM port forwarding
#    or bastion; see scripts/migrate-dynamodb-to-rds.py for the companion
#    data migration).
psql "$CONNECTION_STRING" < infrastructure/database/migrations/001_initial_schema.sql

# 3. Redeploy the API stack wired to the RDS stack + USE_RDS=true.
RDS_STACK_NAME=StreamMyCourse-Rds-integ USE_RDS=true \
  ./scripts/deploy-backend.sh integ

# 4. Run the full integration suite against the RDS-backed API. Passing suite
#    = list/create/enroll/playback round-trip verified on PostgreSQL.
python -m pytest tests/integration -q
```

Rollback (if the smoke test fails):

```bash
# Flip the flag; no redeploy of the RDS stack needed.
USE_RDS=false ./scripts/deploy-backend.sh integ
```

Subsequent runs without the environment overrides leave the feature flag at
its current state (CloudFormation does not reset unset parameter values).

## Cleanup contract

- **Per-test cleanup** is the primary path. The `course_factory` fixture registers a finalizer that calls `DELETE /courses/{id}` for every course it created. Lessons are deleted transitively.
- **Session-end safety net** runs in `pytest_sessionfinish`. It scans the integ DDB table for any course rows whose title still starts with `integ-test-` and deletes them, and empties **all objects** in the integ S3 video bucket (course-scoped keys). Findings are written to stderr and `$GITHUB_STEP_SUMMARY` (in CI) but **never fail** the test job.

## Writing new tests

Use the `api` fixture and the factories rather than calling httpx directly. Example:

```python
def test_publish_requires_ready_lesson(api, course_factory, lesson_factory):
    course = course_factory()
    lesson_factory(course.course_id)
    resp = api.publish_course(course.course_id)
    assert resp.status_code == 400
    assert resp.json()["code"] == "bad_request"
```

Always title test-created entities with `make_test_title(...)` (the factories do this for you) so the safety net can identify and remove leftovers.
