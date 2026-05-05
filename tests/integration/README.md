# Integration tests

HTTPS-driven tests that exercise a deployed backend (API Gateway + Lambda + PostgreSQL catalog + S3) end-to-end.

**CI targets the dev stack** (`streammycourse-api`, `StreamMyCourse-Video-dev`, region `eu-west-1`). The job uses GitHub Environment `dev` so Cognito JWT minting reuses the same secrets/variables as **Verify dev RDS** (`COGNITO_RDS_VERIFY_*`, `COGNITO_RDS_VERIFY_TEST_USERNAME` — see below).

## What gets tested

Every test creates state through the public API, asserts on the API responses, and deletes its state at teardown. Lesson and course cleanup happens via `DELETE /courses/{id}` (course delete cascades to lessons). S3 objects from upload-url tests are removed via boto3 in a session-end safety net (warn-only, never fails CI).

See [`integration_testing_strategy_e5a09a54.plan.md`](../../.cursor/plans/integration_testing_strategy_e5a09a54.plan.md) for the full plan.

## Running locally

Deploy **dev** (matches CI):

```powershell
# from repo root
.\infrastructure\deploy-environment.ps1 -Environment dev
```

Or, on bash / WSL / CI:

```bash
./scripts/deploy-backend.sh dev
```

Then export the resource locations and run pytest:

```bash
export INTEGRATION_API_BASE_URL="$(aws cloudformation describe-stacks \
  --stack-name streammycourse-api \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)"
export INTEGRATION_VIDEO_BUCKET="$(aws cloudformation describe-stacks \
  --stack-name StreamMyCourse-Video-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
  --output text)"
export INTEGRATION_AWS_REGION=eu-west-1

# Required when the pool authorizer protects mutating routes:
# Mint an IdToken (teacher client) or use a static JWT from your Cognito setup.
# export INTEGRATION_COGNITO_JWT='eyJ...'

pip install -r tests/integration/requirements.txt
python -m pytest tests/integration -q
```

PowerShell equivalent:

```powershell
$env:INTEGRATION_API_BASE_URL = (aws cloudformation describe-stacks --stack-name streammycourse-api --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' --output text)
$env:INTEGRATION_VIDEO_BUCKET = (aws cloudformation describe-stacks --stack-name StreamMyCourse-Video-dev --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text)
$env:INTEGRATION_AWS_REGION = 'eu-west-1'

pip install -r tests\integration\requirements.txt
python -m pytest tests\integration -q
```

Helper (deploys dev by default, then resolves stacks and runs pytest):

```powershell
.\scripts\run-integration-tests.ps1
```

Optional **`prod`** against your own stacks: `.\scripts\run-integration-tests.ps1 -Environment prod` (ensure you understand blast radius).

## AWS permissions for local runs

Your AWS profile needs:

- `cloudformation:DescribeStacks` on **streammycourse-api** and **StreamMyCourse-Video-dev**
- `s3:ListBucket`, `s3:DeleteObject` on that environment's video bucket (safety-net cleanup)
- Permissions to mint `admin-initiate-auth` if you script JWT locally (`cognito-idp:AdminInitiateAuth`).

The HTTP test calls themselves only need **`INTEGRATION_COGNITO_JWT`** when routes require auth — they do not otherwise need AWS credentials. AWS credentials power the safety-net cleanup at session end.

## Cognito credentials (CI vs local)

GitHub Deploy workflow **Integration HTTP tests** attaches **`environment: dev`**. Resolve stack outputs against **streammycourse-api** and **StreamMyCourse-Video-dev**, then mint **`INTEGRATION_COGNITO_JWT`** exactly like **`verify-rds-reusable.yml`**: **`StreamMyCourse-Auth-dev`** outputs, **`ADMIN_USER_PASSWORD_AUTH`**, **`TeacherUserPoolClientId`**.

**On GitHub Environment `dev`** (reuse for both Integration HTTP tests and Verify dev RDS):

- **Secret** `COGNITO_RDS_VERIFY_TEST_PASSWORD`
- **Variable** `COGNITO_RDS_VERIFY_TEST_USERNAME` (optional; defaults to `ci-rds-verify@noreply.local`)
- **Secret** `COGNITO_RDS_VERIFY_JWT` (optional fallback if minting fails)

**OIDC:** The Configure AWS Credentials step assumes the **repository** IAM role via job output **`resolve-oidc-deploy-role`** (pins **`vars.AWS_DEPLOY_ROLE_ARN`** in a job without `environment:`) so **`environment: dev`** does not shadow the deploy-role variable.

## Smoke tests (`test_rds_path.py`)

Focused checks for catalog round-trips (create/read/update, lesson FK). Same fixtures as the rest of the suite.

**Dev CI/CD:** [`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml) deploys RDS, applies schema via VPC Lambda, deploys **`deploy-backend-dev`**, runs **Integration HTTP tests**, then **Verify dev RDS** runs `test_rds_path.py` again via **`verify-rds-reusable.yml`**.

**GitHub Actions variable:** Set **`AWS_DEPLOY_ROLE_ARN`** at repo scope (IAM role ARN from **`github-deploy-role-stack.yaml`** output **`GitHubDeployRoleArn`**).

**Bootstrap the CI Cognito user** (operator workstation): see **`scripts/ensure-ci-rds-verify-cognito-user.sh`** and **`COGNITO_RDS_VERIFY_TEST_PASSWORD`** on **`dev`** (and **`prod`** for prod verify).

**Local RDS** (advanced): [`scripts/deploy-rds-stack.sh`](../../scripts/deploy-rds-stack.sh) targets **`dev`** or **`prod`**; integration tests normally follow **`dev`** in CI.

## Test layout

```
tests/integration/
  conftest.py            -- fixtures (api, http_client, course_factory, lesson_factory) + session safety net
  helpers/
    api.py               -- ApiClient wrapping httpx.Client with one method per route
    factories.py         -- course/lesson factory builders + TEST_TITLE_PREFIX
    cleanup.py           -- HTTP + S3 safety-net cleanup utilities
  test_auth_gateway.py   -- `/users/me`, CORS preflight, POST /courses vs Cognito (optional JWT)
  test_*.py              -- one module per scenario group (S1-S5 in the plan)
```

## Cleanup contract

- **Per-test cleanup** is the primary path. The `course_factory` fixture registers a finalizer that calls `DELETE /courses/{id}` for every course it created. Lessons are deleted transitively.
- **Session-end safety net** runs in `pytest_sessionfinish`.
  - **Courses:** lists the CI user's courses with `GET /courses/mine` (requires `INTEGRATION_COGNITO_JWT`) and `DELETE`s any whose title still starts with `integration-test-`. No direct Postgres from the runner.
  - **S3:** empties **all objects** in the configured **non-prod dev** video bucket only (see **`helpers.cleanup.empty_entire_bucket`**). Prod is always refused.
  - Findings go to stderr and `$GITHUB_STEP_SUMMARY` when present but **never fail** CI.

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
