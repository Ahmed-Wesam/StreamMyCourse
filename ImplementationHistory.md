# StreamMyCourse — Implementation History

> Living document tracking all implementation progress, decisions, and milestones.

---

## 2026-05-05 — Catalog Lambda: API Gateway fields in structured logs

### Completed

- [x] **Request context** — [`infrastructure/lambda/catalog/services/common/runtime_context.py`](infrastructure/lambda/catalog/services/common/runtime_context.py) — `extract_apigw_public_fields` (HTTP API + REST), `set_request_path`, `set_upload_kind`; `bind_from_lambda_event` binds stage, domain, route key, client IP, truncated User-Agent.
- [x] **JSON logs** — [`infrastructure/lambda/catalog/services/common/logging_setup.py`](infrastructure/lambda/catalog/services/common/logging_setup.py) — Formatter emits non-empty context fields (including `request_path`, `upload_kind` when set).
- [x] **Handler** — [`infrastructure/lambda/catalog/index.py`](infrastructure/lambda/catalog/index.py) — Sets `request_path` after `apigw_routing_path`.
- [x] **Upload-url branch labels** — [`infrastructure/lambda/catalog/services/course_management/controller.py`](infrastructure/lambda/catalog/services/course_management/controller.py) — `upload_kind` context: `lessonVideo`, `courseThumbnail`, `lessonThumbnail`.
- [x] **Tests** — [`tests/unit/services/common/test_runtime_context.py`](tests/unit/services/common/test_runtime_context.py), [`tests/unit/services/common/test_logging_setup.py`](tests/unit/services/common/test_logging_setup.py).

### Ops

- CloudWatch JSON lines for catalog invocations can include `client_ip` and `user_agent_snippet`; align log retention and access with your privacy posture.

---

## 2026-05-04 — Pre-public release: Security hardening and professional README

### Completed

- [x] **Professional README** — [`README.md`](README.md) — Complete rewrite transforming internal-facing documentation into product-focused presentation; includes architecture mermaid diagram, feature overview for students/instructors, tech stack table, quick start guide, and security section with proprietary notice.
- [x] **Security hardening — IAM policy JSON sanitization** — [`infrastructure/iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json), [`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json), [`infrastructure/iam-trust-github-oidc.json`](infrastructure/iam-trust-github-oidc.json) — Replaced hardcoded AWS account ID `YOUR_AWS_ACCOUNT_ID` with `YOUR_AWS_ACCOUNT_ID` placeholder in all IAM policy files.
- [x] **Security hardening — GitHub variable setup** — Set `AWS_ACCOUNT_ID` GitHub Actions variable on **dev** and **prod** environments via `/use-cli` (AWS) and `/github-cli` (GitHub CLI); same value used for both environments.
- [x] **Security hardening — ImplementationHistory sanitization** — Redacted specific AWS resource identifiers (CloudFront domain, distribution ID, S3 bucket names, account ID references) from historical entries while preserving engineering narrative.
- [x] **Security policy** — [`SECURITY.md`](SECURITY.md) — Created security policy document with vulnerability reporting guidelines, supported versions table, AWS account ID placeholder instructions, and security best practices for operators.

### Ops

- When deploying IAM policies from the JSON files, operators must replace `YOUR_AWS_ACCOUNT_ID` with their actual AWS account ID (retrieved via `aws sts get-caller-identity`).
- The `AWS_ACCOUNT_ID` GitHub variable is set on both dev and prod environments for workflow use.

---

## 2026-05-04 — Operator RDS query Lambda (replaces standalone wipe)

### Completed

- [x] **RDS query / wipe** — [`infrastructure/lambda/rds_query/index.py`](infrastructure/lambda/rds_query/index.py), [`infrastructure/templates/rds-query-stack.yaml`](infrastructure/templates/rds-query-stack.yaml), [`scripts/deploy-rds-query-stack.sh`](scripts/deploy-rds-query-stack.sh), runbook [`infrastructure/database/RDS_QUERY_RUNBOOK.md`](infrastructure/database/RDS_QUERY_RUNBOOK.md) — invoke-only in-VPC Lambda: read-only SQL (allowlisted first-token prefixes), mutating SQL gated by **`allow_mutating_sql`** + stack parameter **`AllowMutatingSql`**, catalog wipe via **`wipe_catalog`** + **`AllowCatalogWipe`**; **`confirm`** matches **`EXPECTED_ENVIRONMENT`**; **`wipe_catalog`** and **`sql`** mutually exclusive; no API Gateway or function URL.
- [x] **Removed standalone wipe** — deleted `infrastructure/lambda/rds_wipe/`, `rds-wipe-stack.yaml`, `deploy-rds-wipe-stack.sh`, `RDS_WIPE_RUNBOOK.md`, and [`tests/unit/test_rds_wipe.py`](tests/unit/test_rds_wipe.py).

### Ops

- Single operator entry point: [**RDS_QUERY_RUNBOOK.md**](infrastructure/database/RDS_QUERY_RUNBOOK.md). Delete legacy CloudFormation stack **`StreamMyCourse-RdsWipe-<env>`** in AWS if it still exists.

- [x] **Read-path DML guard** — same Lambda: `sql_contains_mutating_clause` (regex) blocks **`WITH … DELETE/UPDATE`**, **`SELECT … INTO`**, and other common DML/DDL on the read-only invoke path; see [`tests/unit/test_rds_query.py`](tests/unit/test_rds_query.py).

---

## 2026-05-04 — Video stack: CloudFront OAC + invalidation Lambda wired

### Completed

- [x] **Private S3 via OAC** — [`infrastructure/templates/video-stack.yaml`](infrastructure/templates/video-stack.yaml) — `AWS::CloudFront::OriginAccessControl`; S3 origin uses **`OriginAccessControlId`** and **`S3OriginConfig: {}`**; **`AWS::S3::BucketPolicy`** grants **`s3:GetObject`** to **`cloudfront.amazonaws.com`** with **`AWS:SourceArn`** = this distribution only.
- [x] **Invalidation Lambda in template** — `StreamMyCourse-CfInvalidate-<env>` (`Handler: index.lambda_handler`), IAM **`cloudfront:CreateInvalidation`** scoped to that distribution ARN; [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) and [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1) zip/upload [`cloudfront_invalidation/index.py`](infrastructure/lambda/cloudfront_invalidation/index.py) and pass **`InvalidationLambdaCodeS3Bucket`** / **`InvalidationLambdaCodeS3Key`**; CloudFormation deploy uses **`CAPABILITY_NAMED_IAM`** for named Lambda execution roles.

---

## 2026-05-04 — CloudFront CDN for video streaming (PriceClass_200)

### Completed

- [x] **CloudFront Distribution** — [`infrastructure/templates/video-stack.yaml`](infrastructure/templates/video-stack.yaml) — Added `AWS::CloudFront::Distribution` with:
  - **PriceClass_200**: Covers North America, Europe, Asia, Middle East (free tier eligible: 1TB/month data transfer)
  - **HTTP/2 and HTTP/3**: `HttpVersion: http2and3` for modern performance
  - **CORS passthrough**: Forwards `Origin`, `Access-Control-Request-Headers`, `Access-Control-Request-Method`, `Range`, `If-Range` headers to S3 for HTML5 video streaming
  - **Long cache**: `DefaultTTL: 31536000` (1 year) — videos are immutable at unique UUID-based keys
  - **Query string forwarding**: Enables S3 presigned URL compatibility through CloudFront
  - **HTTPS only**: `ViewerProtocolPolicy: redirect-to-https`

- [x] **S3 CORS update** — Enhanced CORS configuration with extended headers for cross-origin `<video>` element byte-range requests (progressive MP4 playback)

- [x] **Cache invalidation Lambda** — [`infrastructure/lambda/cloudfront_invalidation/index.py`](infrastructure/lambda/cloudfront_invalidation/index.py) — Later **deployed with the video stack** (see **Video stack: CloudFront OAC + invalidation Lambda wired** entry same day); invoke-only `CreateInvalidation` for emergency takedown and future lesson replacement flows.

### Dev Stack Outputs

| Output | Value |
|--------|-------|
| **CloudFront Domain** | `[REDACTED-dev-cf-domain]` |
| **Distribution ID** | `[REDACTED-dev-distribution-id]` |
| **S3 Bucket** | `[REDACTED-dev-video-bucket]` |

### Deploy

- Local dev deploy validated CloudFront distribution creation (10-15 min propagation)
- CI/CD [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) deployed to integ → dev → prod
- All environments now serve video through CloudFront CDN

---

## 2026-05-04 — Video bucket CORS: allow `Range` for cross-origin MP4 playback

### Completed

- [x] **S3 CORS `AllowedHeaders`** — [`infrastructure/templates/video-stack.yaml`](infrastructure/templates/video-stack.yaml) — added **`Range`** and **`If-Range`** so browser preflight succeeds for presigned GET playback from student/teacher origins. Without these, clients may not issue byte-range requests and can buffer for a long time on large MP4s (especially when `moov` is late in the file).

### Ops

- Redeploy **`StreamMyCourse-Video-<env>`** (or equivalent) so the bucket CORS updates; **no** video re-upload required.

---

## 2026-05-04 — Course-scoped S3 keys (`{courseId}/lessons/...`) + optional RDS wipe stack

### Completed

- [x] **S3 object keys** — [`infrastructure/lambda/catalog/services/course_management/storage.py`](infrastructure/lambda/catalog/services/course_management/storage.py) — lesson video `{courseId}/lessons/{lessonId}/video/{uuid}.{ext}`, lesson thumbnail `.../thumbnail/{uuid}.{ext}`, course cover `{courseId}/thumbnail/{uuid}.{ext}`; strict **`presign_get`** full-key patterns (UUID segments); [`service.py`](infrastructure/lambda/catalog/services/course_management/service.py) validator prefixes; [`ports.py`](infrastructure/lambda/catalog/services/course_management/ports.py) `presign_put` gains `course_id` / `lesson_id`.
- [x] **Catalog IAM** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — `S3PresignedUrl` resource ARN widened from `${bucket}/uploads/*` to **`${bucket}/*`** so presigned PUT/GET/DELETE work for the new prefixes (mitigated by Lambda-side key validation).
- [x] **Operator wipe tooling** (superseded by **RDS query Lambda** entry same day) — was a dedicated `rds_wipe` stack + **`RDS_WIPE_RUNBOOK`**; catalog TRUNCATE now runs via **`rds_query`** with **`wipe_catalog`** (see [**RDS_QUERY_RUNBOOK.md**](infrastructure/database/RDS_QUERY_RUNBOOK.md)).
- [x] **Integ cleanup** — [`tests/integration/helpers/cleanup.py`](tests/integration/helpers/cleanup.py) — session safety net empties the **whole** integ video bucket (not only `uploads/`).

### Ops

- Before first deploy of this layout to an environment with legacy **`uploads/`** data: follow [**RDS_QUERY_RUNBOOK.md**](infrastructure/database/RDS_QUERY_RUNBOOK.md) (empty video bucket → invoke catalog wipe via **`rds_query`** → deploy catalog). Order matters so mixed old keys + new `presign_get` never coexist.

---

## 2026-05-04 — Display name without Cognito GetUser; resilient enrollment preview detection

### Completed

- [x] **Header profile** — [`frontend/src/lib/cognito-display-name.ts`](frontend/src/lib/cognito-display-name.ts) — build merged profile from the **ID token** only; removed **`fetchUserAttributes()`** (Cognito **GetUser**, `POST` to `cognito-idp`) so localhost/DevTools no longer shows **400** for display-name resolution when access-token scopes omit **`aws.cognito.signin.user.admin`**. Optional **`poolAttrs`** argument preserves merge tests without a network call. [`cognito-display-name.test.ts`](frontend/src/lib/cognito-display-name.test.ts), [`StudentHeader.dom.test.tsx`](frontend/src/student-app/StudentHeader.dom.test.tsx).
- [x] **Enrollment + preview** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) — **`isEnrollmentRequiredError`** (`code: enrollment_required` or **403** + enrollment message); **`lessonPreviewsToStubLessons`** accepts null/undefined/empty. [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx), [`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx).

---

## 2026-05-04 — Cognito OAuth scopes + enrollment-gated lesson preview UI

### Completed

- [x] **Cognito app clients** — [`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml) — `AllowedOAuthScopes` includes **`aws.cognito.signin.user.admin`** for student and teacher Hosted UI clients so the access token satisfies **GetUser** (Amplify **`fetchUserAttributes`**) and clears **`NotAuthorizedException` / `Access Token does not have required scopes`** on load.
- [x] **SPA Amplify** — [`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts) — OAuth **`scopes`** list matches the app client; [`SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx) test config aligned.
- [x] **Enrollment-required flows** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) — shared **`lessonPreviewsToStubLessons`** for anonymous **`GET /courses/:id/preview`** outline rows. [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx) and [`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx) load that preview when **`enrollment_required`** so users still see lesson titles; lesson player disables sidebar links and prev/next until enrolled, and sets **course** from preview when **`getCourse`** never ran.

### Ops

- Deploy **auth stack** and **rebuild student + teacher SPAs** after merge; users should **sign out and sign in again** so tokens are minted with the new scope.

---

## 2026-05-04 — Enrollment reliability: Cognito PostAuthentication user sync + enroll-time profile upsert

### Completed

- [x] **Cognito → RDS** — New Lambda [`infrastructure/lambda/cognito_user_profile_sync/handler.py`](infrastructure/lambda/cognito_user_profile_sync/handler.py) (`PostAuthentication`): idempotent `users` UPSERT (same SQL contract as catalog `UserProfileRdsRepository.put_profile`); failures are logged and **do not** block login.
- [x] **IaC** — [`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml) — optional VPC Lambda, IAM, `LambdaConfig.PostAuthentication`, parameters `RdsStackName`, `EnableUserProfileSync`, `CognitoUserProfileSyncCodeS3Bucket` / `Key`.
- [x] **CI** — [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — package sync zip, deploy auth with RDS + sync flags (**dev** / **prod**); **`CAPABILITY_NAMED_IAM`** for named sync role. [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — Vulture/Radon include the new Lambda tree.
- [x] **Catalog API** — [`services/course_management/controller.py`](infrastructure/lambda/catalog/services/course_management/controller.py) — required [`UserProfileProvisioner`](infrastructure/lambda/catalog/services/course_management/ports.py); **enroll** calls `get_or_create_profile` before `enroll_in_published_course`. [`index.py`](infrastructure/lambda/catalog/index.py) passes `auth_service` into `handle`.
- [x] **Boundaries** — [`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py) scans `cognito_user_profile_sync`; `repo.py` holds boto3 + psycopg2.
- [x] **Student SPA** — [`StudentProfileBootstrap`](frontend/src/components/auth/StudentProfileBootstrap.tsx) + Vitest; mounted in [`student-app/App.tsx`](frontend/src/student-app/App.tsx).
- [x] **Local deploy** — [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1) — optional auth params for sync Lambda + `CAPABILITY_NAMED_IAM` on auth template.

### Ops

- First deploy with sync needs **RDS stack exports** present in the account (same region as auth). Re-deploy **auth** after changing sync code so `CognitoUserProfileSyncCodeS3Key` updates.

---

## 2026-05-04 — Instructor dashboard: GET /courses/mine (draft + published)

### Completed

- [x] **API** — [`infrastructure/lambda/catalog/services/course_management/controller.py`](infrastructure/lambda/catalog/services/course_management/controller.py) — `GET /courses/mine` (routed before `/courses/{id}`) returns `as_course_list` for **teachers** (filter `created_by` = Cognito `sub`) and **admins** (all courses); when auth is not enforced, same “dev” behavior as other routes (full `list_courses()`).
- [x] **Service** — [`service.py`](infrastructure/lambda/catalog/services/course_management/service.py) — `list_instructor_courses` uses `_public_course_dict` + lesson-thumbnail fallback for hero images.
- [x] **Repo** — [`ports.py`](infrastructure/lambda/catalog/services/course_management/ports.py), [`rds_repo.py`](infrastructure/lambda/catalog/services/course_management/rds_repo.py), [`repo.py`](infrastructure/lambda/catalog/services/course_management/repo.py) — `list_courses_by_instructor` (RDS `ORDER BY created_at ASC`; Dynamo filter + sort by `createdAt`).
- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — resource `/courses/mine`, `GET` + `OPTIONS`, Cognito authorizer when `HasCognitoAuthorizer`; deployment logical id **CatalogApiDeploymentV8** (bump so stage picks up new methods).
- [x] **Teacher UI** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) `listInstructorCourses`, [`InstructorDashboard.tsx`](frontend/src/pages/InstructorDashboard.tsx) uses it instead of public `GET /courses`.
- [x] **Tests** — [`tests/unit/services/course_management/test_service.py`](tests/unit/services/course_management/test_service.py), [`test_controller.py`](tests/unit/services/course_management/test_controller.py), [`test_repo.py`](tests/unit/services/course_management/test_repo.py), [`test_rds_repos.py`](tests/unit/test_rds_repos.py).

### Ops

- Deploy **API stack** after merge so API Gateway exposes `GET /courses/mine` before relying on the new teacher build in a given environment.

---

## 2026-05-04 — Docs: deployed dev/prod use RDS only; DynamoDB catalog deprecated

### Completed

- [x] **Contract alignment** — [`design.md`](design.md), [`roadmap.md`](roadmap.md) — **managed dev and prod** run the catalog API on **RDS PostgreSQL** (`USE_RDS=true`); **DynamoDB** is **deprecated** there and is **not** used for application traffic. The Lambda still implements the DynamoDB repo path for **local / emergency rollback** only. Linked [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md), [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql), and deploy pipeline job names (`deploy-rds-dev` / `deploy-rds-prod`, etc.).

---

## 2026-05-04 — Repo root: product readme, proprietary license, remove actionlint vendor docs

### Completed

- [x] **Root readme** — [`README.md`](README.md) — replaced mistaken upstream **actionlint** readme with a short StreamMyCourse overview, maintainer pointers (`AGENTS.md`, `design.md`), and layout table; states the repository is not for public redistribution.
- [x] **License** — [`LICENSE.txt`](LICENSE.txt) — **proprietary / all rights reserved** (replaces rhysd MIT text that shipped with the old readme).
- [x] **Cleanup** — removed repository root **`docs/*.md`** files that were **vendored actionlint documentation** (`checks.md`, `install.md`, `usage.md`, etc.). Product docs remain under [`infrastructure/docs/`](infrastructure/docs/).
- [x] **Cursor skill** — [`.cursor/skills/review-and-commit/SKILL.md`](.cursor/skills/review-and-commit/SKILL.md) — **`/review_and_commit`** workflow (review pending changes, fix findings, then **`/commit`** without push unless asked).

---

## 2026-05-04 — Auth UI: consistent header display name (Cognito profile merge)

### Completed

- [x] **Display name** — [`frontend/src/lib/cognito-display-name.ts`](frontend/src/lib/cognito-display-name.ts) — if the user pool returns **empty** profile strings, **restore non-empty ID token claims** (e.g. `given_name` from hosted UI) after merge so student and teacher chrome match; for **email-shaped** Cognito usernames, the short label uses the **local part** of the address.
- [x] **Tests** — [`frontend/src/lib/cognito-display-name.test.ts`](frontend/src/lib/cognito-display-name.test.ts) — token `given_name` kept when pool sends blank `given_name`; email-username case expects local part.

---

## 2026-05-04 — Course delete: DB-first, NotFound for missing id, S3 client timeouts

### Completed

- [x] **Service** — [`infrastructure/lambda/catalog/services/course_management/service.py`](infrastructure/lambda/catalog/services/course_management/service.py) — `delete_course` raises **`NotFound`** when the course id does not exist (fixes **admin** `DELETE` on a random UUID previously returning `deleted: true`). **Persist `delete_course_and_lessons` before S3 cleanup** so the catalog updates even if S3 is slow; S3 remains best-effort via `_delete_media_keys`.
- [x] **Storage** — [`infrastructure/lambda/catalog/services/course_management/storage.py`](infrastructure/lambda/catalog/services/course_management/storage.py) — S3 client **`connect_timeout=5`**, **`read_timeout=15`** to reduce unbounded hangs on `delete_objects`.
- [x] **Tests** — [`tests/unit/services/course_management/test_service.py`](tests/unit/services/course_management/test_service.py), [`tests/unit/services/course_management/test_storage.py`](tests/unit/services/course_management/test_storage.py), [`tests/unit/services/course_management/test_controller.py`](tests/unit/services/course_management/test_controller.py) — NotFound, DB-before-S3 order, controller **404**, Config timeouts.

### Ops note

- Prod **`DELETE`** can still hit the **30s Lambda limit** if many/large S3 deletes exceed wall-clock budget; the **RDS row is removed first**, so **`GET /courses`** reflects the delete even when the invocation errors with timeout. Optional follow-up: raise **`Timeout`** in [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) or shorten/async S3 cleanup.

---

## 2026-05-04 — API and client: no-store for JSON (stale course list after delete)

### Completed

- [x] **Lambda** — [`infrastructure/lambda/catalog/services/common/http.py`](infrastructure/lambda/catalog/services/common/http.py) — `Cache-Control: no-store` on **all** successful JSON responses (not only 4xx/5xx), so `GET /courses` and other catalog reads are not served from HTTP caches after mutations (e.g. `DELETE /courses/{id}`).
- [x] **Frontend** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) — `fetch` with `cache: 'no-store'` for API calls (including `getUploadUrl`).
- [x] **Tests** — [`tests/unit/services/common/test_http.py`](tests/unit/services/common/test_http.py) — assert `no-store` on 200/201 JSON responses.

---

## 2026-05-04 — RDS verify: reusable workflow + unified Environment secrets

### Completed

- [x] **Reusable workflow** — [`.github/workflows/verify-rds-reusable.yml`](.github/workflows/verify-rds-reusable.yml) — single implementation for stack resolution, Cognito mint / JWT fallback, and **`pytest test_rds_path.py`**. Job attaches **`environment: ${{ inputs.github_environment }}`** so secrets/vars resolve per **dev** or **prod** without cross-environment names in YAML. **OIDC role** is passed as input **`aws_deploy_role_arn`** from caller **`${{ vars.AWS_DEPLOY_ROLE_ARN }}`** (repository **Actions variable**; `secrets` is not available in `workflow_call` `with:` on the caller). **Fix (2026-05-04):** first Deploy run failed **`configure-aws-credentials`** empty role — resolved by repository variable + input wiring.
- [x] **Deploy workflow** — [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — **`verify-dev-rds`** / **`verify-prod-rds`** only pass **`github_environment`** plus **CloudFormation stack inputs** (no `workflow_call` secret mapping; avoids invalid `environment` + `uses` on the same job).
- [x] **GitHub naming** — **dev** and **prod** environments each expose the **same keys**: **`COGNITO_RDS_VERIFY_TEST_PASSWORD`**, optional **`COGNITO_RDS_VERIFY_JWT`**, optional variable **`COGNITO_RDS_VERIFY_TEST_USERNAME`** (values differ per environment). Retired per-environment-suffixed **`COGNITO_RDS_VERIFY_DEV_*` / `COGNITO_RDS_VERIFY_PROD_*`** for verify jobs, and legacy **`INTEG_*_COGNITO_*`**.
- [x] **Contract tests** — [`tests/unit/test_deploy_backend_workflow_contract.py`](tests/unit/test_deploy_backend_workflow_contract.py) — reusable has no literal dev/prod stack names; callers wire stacks + **`github_environment`** only.
- [x] **Docs / script** — [`tests/integration/README.md`](tests/integration/README.md), [`design.md`](design.md), [`scripts/ensure-ci-rds-verify-cognito-user.sh`](scripts/ensure-ci-rds-verify-cognito-user.sh), [`tests/integration/conftest.py`](tests/integration/conftest.py), [`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml) comment.

### Operator rollout

1. On GitHub **dev** and **prod** environments: create **`COGNITO_RDS_VERIFY_TEST_PASSWORD`**, optional **`COGNITO_RDS_VERIFY_JWT`**, optional variable **`COGNITO_RDS_VERIFY_TEST_USERNAME`** (copy from vault; GitHub does not reveal old secrets after delete).
2. Merge workflow to **`main`**, confirm **Verify dev RDS** / **Verify prod RDS** green.
3. Delete obsolete suffixed secrets/variables (**`COGNITO_RDS_VERIFY_DEV_*`**, **`COGNITO_RDS_VERIFY_PROD_*`**, and any remaining **`INTEG_*_COGNITO_*`**) with `gh secret delete` / `gh variable delete` and `-e dev` / `-e prod`.

---

## 2026-05-04 — Option B: layout `chromeHeader`, remove legacy `Header`

### Completed

- [x] **`Layout`** — [`frontend/src/components/layout/Layout.tsx`](frontend/src/components/layout/Layout.tsx) — optional **`chromeHeader`** (fixed app nav); main column uses **`pt-20`** when set (clears **`h-16`** bar plus air gap so content does not sit flush under the header); removed legacy **`showMarketingHeader`** / marketing **`Header`** integration.
- [x] **Student / teacher shells** — [`frontend/src/student-app/App.tsx`](frontend/src/student-app/App.tsx), [`frontend/src/teacher-app/App.tsx`](frontend/src/teacher-app/App.tsx) — pass **`chromeHeader={<StudentHeader />}`** / **`<TeacherHeader />`**; routes + **`PostLoginRedirect`** live inside **`Layout`** children only.
- [x] **`LessonPlayerPage`** — [`frontend/src/pages/LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx) — dropped standalone **`Header`** and duplicate full-page gradient; uses the same student shell as catalog/detail.
- [x] **Removed** — **`Header.tsx`** and **`Header.dom.test.tsx`** from **`frontend/src/components/layout/`** — superseded by **`StudentHeader`** + tests in [`frontend/src/student-app/StudentHeader.dom.test.tsx`](frontend/src/student-app/StudentHeader.dom.test.tsx); layout contract tests in [`frontend/src/components/layout/Layout.dom.test.tsx`](frontend/src/components/layout/Layout.dom.test.tsx).
- [x] **`useCognitoDisplayName`** — [`frontend/src/lib/cognito-display-name.ts`](frontend/src/lib/cognito-display-name.ts) — **`ready`** until merged profile attributes resolve; [`StudentHeader`](frontend/src/student-app/StudentHeader.tsx) / [`TeacherHeader`](frontend/src/teacher-app/TeacherHeader.tsx) hide the label until ready to avoid flashing raw federated **`Google_…`** usernames; hook tests in [`cognito-display-name.test.ts`](frontend/src/lib/cognito-display-name.test.ts).

---

## 2026-05-04 — Remove legacy unified SPA entry (dual-build only)

### Completed

- [x] **Deleted** — `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/vite.config.ts` — the old combined app duplicated student + teacher routes (including **unprotected `/instructor`** on the student bundle). Production already used `student-main.tsx` / `teacher-main.tsx` only; knip entry points matched that reality.
- [x] **`frontend/index.html` restored (minimal)** — Vite **`npm run dev`** serves **`/`** from root **`index.html`**; without it the app was a blank page. The file now mirrors **`student.html`** (loads **`student-main.tsx`** only); it is **not** the legacy **`App.tsx`** entry. Production **`build:student`** still uses **`student.html`** → **`dist/student/index.html`** only.
- [x] **Student Vite** — [`frontend/vite.student.config.ts`](frontend/vite.student.config.ts) — explicit **`student.html`** Rollup input + **`closeBundle`** rename to **`dist/student/index.html`** (parity with teacher build), so the student build no longer depends on a root `index.html`.
- [x] **Scripts** — [`frontend/package.json`](frontend/package.json) — **`dev`**, **`build`**, and **`preview`** use **`vite.student.config.ts`**; local default dev is the student site (port 5173).
- [x] **Docs / env** — [`design.md`](design.md) component tree + §10 notes; [`frontend/.env.example`](frontend/.env.example) proxy comment now references **`vite.student.config.ts`**.

### Notes

- **`npm run dev:teacher`** unchanged (port 5174). **`LessonPlayerPage`** shell alignment and **`Layout`** **`chromeHeader`** shipped in **Option B** (same-day entry above).

### Follow-up (same day) — duplicate student / teacher headers (superseded by Option B)

- [x] **`Layout`** — interim **`showMarketingHeader={false}`** so marketing **`Header`** did not stack with **`StudentHeader`** / **`TeacherHeader`**; superseded by **`chromeHeader`** + removal of **`Header.tsx`**.
- [x] **Pages** — removed nested **`Layout`** from **`CourseCatalogPage`**, **`CourseDetailPage`**, **`InstructorDashboard`**, **`CourseManagement`** so route content is not wrapped in a second full chrome stack.

---

## 2026-05-04 — Artifact Janitor Lambda for S3 cleanup

### Completed

- [x] **Lambda** — [`infrastructure/lambda/artifact_janitor/index.py`](infrastructure/lambda/artifact_janitor/index.py) — Python 3.11 scheduled cleanup of old Lambda deployment artifacts; groups by `(type, environment)`, keeps 2 most recent, deletes rest; configurable via `KEEP_COUNT` and `DRY_RUN` env vars.
- [x] **Infrastructure** — [`infrastructure/templates/artifact-janitor-stack.yaml`](infrastructure/templates/artifact-janitor-stack.yaml) — CloudFormation stack with Lambda, IAM role (S3 List/Delete), EventBridge `rate(1 day)` schedule, CloudWatch logs, and error alarm.
- [x] **Deployment scripts** — [`scripts/deploy-janitor.sh`](scripts/deploy-janitor.sh) (Linux/macOS) and [`scripts/deploy-janitor.ps1`](scripts/deploy-janitor.ps1) (Windows) — package Lambda, create/update stack, deploy code.
- [x] **S3 Lifecycle backup** — 90-day retention rule on artifact bucket as safety net if Lambda fails.

### Ops

- Deployed to dev: `StreamMyCourse-ArtifactJanitor-dev` with daily schedule.
- First run cleaned **186 artifacts** (~104 MB), leaving 11 objects (2 per group + edge cases).
- Manual trigger: `aws lambda invoke --function-name StreamMyCourse-ArtifactJanitor-dev --region eu-west-1 response.json`
- View logs: `aws logs tail /aws/lambda/StreamMyCourse-ArtifactJanitor-dev --region eu-west-1 --follow`

---

## 2026-05-04 — Prod RDS PostgreSQL via Deploy workflow

### Completed

- [x] **CI/CD** — [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — **`deploy-rds-prod`** (schema-applier zip + `StreamMyCourse-Rds-prod` + wait **`streammycourse-prod`**) → **`apply-schema-prod`** (Lambda invoke, assert `{"ok":true}`) → **`deploy-backend-prod`** gains **`needs`** on both jobs, **`env`** **`RDS_STACK_NAME` / `USE_RDS=true`**, and stricter **`if`** on RDS/schema success → **`verify-prod-rds`** (pytest **`test_rds_path.py`** vs **`StreamMyCourse-Api-prod`** via **`verify-rds-reusable.yml`**; GitHub **prod** Environment secrets **`COGNITO_RDS_VERIFY_*`** unified keys; see **2026-05-04 — RDS verify: reusable workflow + unified Environment secrets**).
- [x] **Workflow contract tests** — [`tests/unit/test_deploy_backend_workflow_contract.py`](tests/unit/test_deploy_backend_workflow_contract.py) — asserts prod RDS job names and **`deploy-backend-prod`** block contents (no PyYAML).
- [x] **Bootstrap script** — [`scripts/ensure-ci-rds-verify-cognito-user.sh`](scripts/ensure-ci-rds-verify-cognito-user.sh) — **`CI_RDS_VERIFY_AUTH_STACK`** `*-prod` vs dev prints hint to store password in **`COGNITO_RDS_VERIFY_TEST_PASSWORD`** on the matching GitHub Environment.
- [x] **Local RDS deploy** — [`scripts/deploy-rds-stack.sh`](scripts/deploy-rds-stack.sh) mirrors CI packaging + deploy + `aws rds wait` (Git Bash on Windows; Python zip fallback if `zip` missing); guard [`tests/unit/test_deploy_rds_stack_script.py`](tests/unit/test_deploy_rds_stack_script.py) (`bash -n`).
- [x] **Docs** — [`tests/integration/README.md`](tests/integration/README.md) prod verify + migration window + local preflight; [`design.md`](design.md) §10 prod RDS bullets.

### Operator checklist (before first green **verify-prod-rds**)

1. **`CI_RDS_VERIFY_AUTH_STACK=StreamMyCourse-Auth-prod`** + password → **`ensure-ci-rds-verify-cognito-user.sh`**.
2. GitHub **prod** Environment secret **`COGNITO_RDS_VERIFY_TEST_PASSWORD`** (and optional **`COGNITO_RDS_VERIFY_JWT`**).
3. Run **`migrate-dynamodb-to-rds.py`** for **`StreamMyCourse-Catalog-prod`** during the pipeline window after schema apply if prod DynamoDB has data (idempotent; not in CI).
4. Push **`main`** (or **Deploy** `workflow_dispatch` **full**) and confirm **Verify prod RDS** is green; smoke teacher site → catalog / playback.

---

## 2026-05-04 — CORS fail-secure, CSP headers, and audit logging

### Completed

- [x] **CORS defaults** — [`infrastructure/lambda/catalog/config.py`](infrastructure/lambda/catalog/config.py) — `ALLOWED_ORIGINS` unset, whitespace-only, or comma-only CSV yields an **empty** allowlist (no implicit `*`); explicit `ALLOWED_ORIGINS=*` still maps to wildcard for deliberate dev/tools.
- [x] **Handler gate** — [`infrastructure/lambda/catalog/index.py`](infrastructure/lambda/catalog/index.py) — after `load_config()`, empty allowlist returns **503** with `code: cors_misconfigured`, omits CORS response headers, logs **WARNING**, and **does not** call `lambda_bootstrap()`.
- [x] **HTTP helpers** — [`infrastructure/lambda/catalog/services/common/http.py`](infrastructure/lambda/catalog/services/common/http.py) — `pick_origin([])` returns `None`; `json_response` / `options_response` accept optional origin and omit CORS keys when `None`; conservative **`Content-Security-Policy`** on JSON and OPTIONS responses.
- [x] **Audit events** — [`infrastructure/lambda/catalog/services/course_management/controller.py`](infrastructure/lambda/catalog/services/course_management/controller.py) — INFO `audit_event` after successful **enrollment** and **course delete** with `audit_action`, `course_id`, `user_sub_prefix` (first 8 chars of Cognito `sub` only).
- [x] **Typing** — [`infrastructure/lambda/catalog/services/auth/controller.py`](infrastructure/lambda/catalog/services/auth/controller.py) — `handle_users_me` accepts optional origin for consistency with `json_response`.

### Tests

- Updated [`tests/unit/test_config.py`](tests/unit/test_config.py); expanded [`tests/unit/services/common/test_http.py`](tests/unit/services/common/test_http.py); [`tests/unit/test_index.py`](tests/unit/test_index.py) + autouse `ALLOWED_ORIGINS` for handler tests; [`tests/unit/test_index_logging.py`](tests/unit/test_index_logging.py) + misconfig warning test; [`tests/unit/services/course_management/test_controller_logging.py`](tests/unit/services/course_management/test_controller_logging.py) audit assertions.

### Docs

- [`design.md`](design.md) — CORS misconfiguration and security bullets updated.

### Ops

- Deployed stacks already pass `ALLOWED_ORIGINS` from `CorsAllowOrigin`; local invokes and tests must set the env explicitly.

---

## 2026-05-03 — Structured JSON Logging for Lambda

### Completed

- [x] **Common logging modules** — [`infrastructure/lambda/catalog/services/common/logging_setup.py`](infrastructure/lambda/catalog/services/common/logging_setup.py) — JSON formatter with `timestamp`, `level`, `logger`, `message`, `lambda_request_id`, `api_request_id`, `action`, `duration_ms`, `status_code` fields. `configure_logging()` reads `LOG_LEVEL` env var (default INFO). Debug warning emitted at startup when level is DEBUG.
- [x] **Runtime context** — [`infrastructure/lambda/catalog/services/common/runtime_context.py`](infrastructure/lambda/catalog/services/common/runtime_context.py) — `contextvars` for correlation IDs (`lambda_request_id` from Lambda context, `api_request_id` from API Gateway), `http_method`, `route_or_action`. Helpers: `bind_request_context()`, `clear_request_context()`, `bind_from_lambda_event()`, `update_action()`.
- [x] **Handler wireup** — [`infrastructure/lambda/catalog/index.py`](infrastructure/lambda/catalog/index.py) — calls `configure_logging()` at module load (cold start), `bind_from_lambda_event()` at request start, logs request completion with `method`, `path`, `status_code`, `duration_ms`, cleans up context in `finally`.
- [x] **Controller action logging** — [`services/course_management/controller.py`](infrastructure/lambda/catalog/services/course_management/controller.py) and [`services/auth/controller.py`](infrastructure/lambda/catalog/services/auth/controller.py) — call `update_action(action)` after routing; log `HttpError` at INFO with `status_code` and `error_code`; log unexpected exceptions at ERROR with `exc_info`.
- [x] **rds_schema_apply alignment** — [`infrastructure/lambda/rds_schema_apply/index.py`](infrastructure/lambda/rds_schema_apply/index.py) — duplicated JSON logging setup (~40 lines), `LOG_LEVEL` support, structured logs for DDL execution and completion.
- [x] **CloudFormation** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — new parameter `LogLevel` (DEBUG/INFO/WARNING/ERROR/CRITICAL) passed to Lambda as `LOG_LEVEL` env var.
- [x] **Config** — [`infrastructure/lambda/catalog/config.py`](infrastructure/lambda/catalog/config.py) — `AppConfig.log_level` field populated from `LOG_LEVEL` env var.

### Security / Design Decisions

- **PII handling**: Per user requirement, PII (emails, JWTs, request bodies) is **logged as-is** without redaction at all levels (DEBUG/INFO/WARNING/ERROR). This simplifies debugging but requires operator awareness when enabling DEBUG in production.
- **JSON structure**: One JSON object per line; CloudWatch Logs Insights compatible fields (`timestamp`, `level`, `action`, `status_code`, `duration_ms`).
- **No new dependencies**: Uses stdlib `logging`, `json`, `contextvars` only (no Powertools).
- **Boundary compliance**: New modules stay in `services/common/`; no `boto3` outside repo/storage per existing rules.

### Tests

- 12 tests for `logging_setup.py` (JSON format, exception handling, log injection protection)
- 13 tests for `runtime_context.py` (binding, clearing, request ID extraction, isolation)
- 8 tests for `index.py` logging integration (context binding, cleanup, request completion)
- 6 tests for controller logging (action field, HTTP error logging, exception handling)
- 10 tests for PII handling (verification that data is logged as-is)
- **Total**: 366 unit tests passing; boundary check passes.

### Operational Notes

- Set environment variable `LOG_LEVEL=DEBUG` (via stack parameter or env) to enable verbose logging with startup warning.
- Sample CloudWatch Logs Insights query: `fields @timestamp, level, action, status_code, duration_ms | filter action == "get_course" | sort @timestamp desc | limit 20`

---

## 2026-05-03 — Verify dev RDS: mint Cognito JWT in Deploy (password secret + legacy fallback)

### Completed

- [x] **Deploy workflow** — Historically **`verify-dev-rds`** inlined Cognito mint against **`StreamMyCourse-Auth-dev`**. **Current shape:** [`.github/workflows/verify-rds-reusable.yml`](.github/workflows/verify-rds-reusable.yml) + unified GitHub Environment keys — see **2026-05-04 — RDS verify: reusable workflow + unified Environment secrets**.
- [x] **Operator bootstrap script** — [`scripts/ensure-ci-rds-verify-cognito-user.sh`](scripts/ensure-ci-rds-verify-cognito-user.sh) — creates **`ci-rds-verify@noreply.local`** (if missing), sets permanent password when **`CI_RDS_VERIFY_PASSWORD`** is set, ensures **`custom:role=teacher`**.
- [x] **Docs** — [`tests/integration/README.md`](tests/integration/README.md) — operator steps for RDS verify + bootstrap.

### IAM

- **No template/JSON change** — OIDC deploy role already includes **`cognito-idp:*`** in **`eu-west-1`** in [`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) / [`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml). After policy edits, sync live IAM with [`scripts/apply-github-deploy-role-policies.sh`](scripts/apply-github-deploy-role-policies.sh) or redeploy the bootstrap stack.

### Operator checklist (GitHub **dev** environment)

1. Run **`CI_RDS_VERIFY_PASSWORD='…' ./scripts/ensure-ci-rds-verify-cognito-user.sh`** (AWS admin) once.
2. Set **`COGNITO_RDS_VERIFY_TEST_PASSWORD`** on the **dev** environment to the same password; optional variable **`COGNITO_RDS_VERIFY_TEST_USERNAME`** (defaults to **`ci-rds-verify@noreply.local`**).
3. Optional: **`COGNITO_RDS_VERIFY_JWT`** for emergency fallback; refresh when it expires if minting is broken.
4. After merge to **`main`**, confirm **Deploy** → **Verify dev RDS** is green (canary).

---

## 2026-05-03 — Resilient thumbnail presigning in course/lesson lists

### Completed

- [x] **Service hardening** — [`infrastructure/lambda/catalog/services/course_management/service.py`](infrastructure/lambda/catalog/services/course_management/service.py) — added **`_safe_presign_get`** so one invalid or legacy S3 key does not make **`GET /courses/{id}/lessons`** or published catalog payloads fail with **400** for the whole list; **`get_playback_url`** still calls strict **`presign_get`** so invalid **video** keys fail on the playback route only.
- [x] **Regression tests** — [`tests/unit/test_course_management_service.py`](tests/unit/test_course_management_service.py) — covers mixed good/bad lesson thumbnails, bad course cover keys, and unchanged strict playback signing.

### Context

- **Symptom cluster (historical):** “Thumbnails and playback broke together” often traced to **`list_lessons` returning 400** when **`CourseMediaStorage.presign_get`** rejected a key; **`_safe_presign_get`** (2026-05-03) and later **course-scoped key validation** (2026-05-04) address this—separate from API Gateway **OPTIONS** on **`/playback/...`** (already fixed in the template).

---

## 2026-05-03 — API Gateway OPTIONS for playback (CORS preflight)

### Completed

- [x] **Playback CORS** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — added **`PlaybackOptionsMethod`** (`OPTIONS` on `/playback/{courseId}/{lessonId}`, `AuthorizationType: NONE`, AWS_PROXY to the catalog Lambda) so browsers get a **204** CORS response before credentialed **`GET`**; renamed deployment **`CatalogApiDeploymentV6` → `CatalogApiDeploymentV7`** and pointed **`CatalogApiStage`** at the new snapshot so the stage picks up the method.

### Context

- **Symptom:** Student SPA (`https://dev.streammycourse.click`) called **`GET /playback/...`** with **`Authorization`**; the browser’s **OPTIONS** preflight hit API Gateway with **no** `OPTIONS` method on that resource, so DevTools showed CORS failures and **`net::ERR_FAILED`** even though **`GET`** remained the authorized path.

---

## 2026-05-03 — VPC schema-applier Lambda (CI `apply-schema-dev` without runner → RDS TCP)

### Completed

- [x] **In-VPC migrator** — [`infrastructure/lambda/rds_schema_apply/index.py`](infrastructure/lambda/rds_schema_apply/index.py) — Lambda handler reads **`SECRET_ARN`**, pulls RDS JSON from Secrets Manager, runs bundled **`schema.sql`** (copy of [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) at zip build time) via **`psycopg2`** with **`sslmode=require`**, statement-splitting safe for the current DDL file.
- [x] **`rds-stack.yaml`** — parameters **`SchemaApplierCodeS3Bucket`** / **`SchemaApplierCodeS3Key`** (optional; both empty skips the Lambda); resources **`SchemaApplierLambdaRole`** + **`SchemaApplierLambda`** (`StreamMyCourse-RdsSchemaApplier-${Environment}`, same private subnet + Lambda SG as the catalog function); export **`SchemaApplierFunctionName`** when present.
- [x] **Deploy workflow** — [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — `deploy-rds-dev` builds the zip (Linux **`psycopg2-binary`** wheel), uploads to **`streammycourse-artifacts-<account>-eu-west-1`**, passes bucket/key into **`aws cloudformation deploy`**; `apply-schema-dev` replaces **`psql`** with **`aws lambda invoke`** + **`jq`** assert on **`{"ok":true}`**.

---

## 2026-05-03 — RDS PostgreSQL dev rollout via CI/CD (deploy pipeline + smoke tests)

### Completed

- [x] **CI validation** — [`.github/workflows/ci.yml`](.github/workflows/ci.yml) — added [`infrastructure/templates/rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) to the CloudFormation parse step so RDS template breakage is caught pre-merge.
- [x] **Deploy pipeline (dev)** — [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — three new jobs chain after `integ-tests`:
  - **`deploy-rds-dev`** — builds a **schema-applier** zip (`infrastructure/lambda/rds_schema_apply/index.py` + vendored **`psycopg2-binary`** + copied **`001_initial_schema.sql`** as `schema.sql`), uploads to **`streammycourse-artifacts-<account>-<region>`**, then `aws cloudformation deploy` for `StreamMyCourse-Rds-dev` with **`SchemaApplierCodeS3Bucket`** / **`SchemaApplierCodeS3Key`**, then `aws rds wait db-instance-available` on `streammycourse-dev`.
  - **`apply-schema-dev`** — resolves **`SchemaApplierFunctionName`** from stack outputs and runs **`aws lambda invoke`** (payload `{}`); the Lambda runs in the **private subnet** with the catalog **Lambda SG**, reads **`SECRET_ARN`** from env, fetches JSON from Secrets Manager, and executes the bundled DDL with **`psycopg2`** + **`sslmode=require`** (no credentials on the GitHub runner, no TCP 5432 from the runner).
  - **`verify-dev-rds`** — calls **`verify-rds-reusable.yml`** with **`github_environment: dev`** and dev stack inputs; exports **`INTEG_*`** + **`INTEG_COGNITO_JWT`**, then runs **`test_rds_path.py`** with **`USE_RDS=true`**.
- [x] **Dev backend wiring** — [`deploy-backend-dev`](.github/workflows/deploy-backend.yml) job now sets **`RDS_STACK_NAME=StreamMyCourse-Rds-dev`** + **`USE_RDS=true`** as job-level env vars and depends on `deploy-rds-dev` + `apply-schema-dev`. [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) already forwards both to `aws cloudformation deploy` as `RdsStackName` / `UseRds` parameter overrides (no script change needed).
- [x] **Integration smoke tests** — [`tests/integration/test_rds_path.py`](tests/integration/test_rds_path.py) — RDS-only coverage using the existing `api` / `course_factory` / `lesson_factory` fixtures. `pytestmark = pytest.mark.skipif(not USE_RDS)` so local and non-RDS CI runs skip cleanly; tests assert POST/GET round-trip, PUT persistence, and lesson FK insertion against whichever backend is wired.

### Infra follow-up (manual / non-CI deploys)

- **`rds-stack.yaml`** parameters **`SchemaApplierCodeS3Bucket`** / **`SchemaApplierCodeS3Key`** default to empty — omitting them skips the applier Lambda (useful for accounts that only want VPC+RDS and will run **`psql`** from a bastion). CI always passes both so **`StreamMyCourse-RdsSchemaApplier-dev`** exists and **`apply-schema-dev`** can invoke it.

### Decisions

- **Dev over a new `beta` environment** — no users means no maintenance window is needed; existing `dev` GitHub Environment already has OIDC + secrets.
- **No dedicated health endpoint** — integration tests against the deployed API are a stronger signal (exercise real adapters, FKs, and serializers) than a `/health` probe and don't grow the public surface.
- **Feature flag remains the rollback path** — `USE_RDS=false` + redeploy reverts in minutes; the DynamoDB stack stays intact until the operator explicitly tears it down.

### Deferred to operator (post-merge)

- First full **dev** pipeline run on AWS (RDS stack + schema Lambda + `USE_RDS=true` + `verify-dev-rds`) and a rollback drill. Plan: [`.cursor/plans/rds_dev_rollout_ci_cd_39a30e0b.plan.md`](.cursor/plans/rds_dev_rollout_ci_cd_39a30e0b.plan.md).

---

## 2026-05-03 — RDS PostgreSQL migration scaffold (feature-flagged, `USE_RDS=false` default)

### Completed

- [x] **Infra (new stack)** — [`infrastructure/templates/rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) — 1-AZ VPC (public + private subnets, no NAT), **private** RDS **PostgreSQL 16** **`db.t4g.micro`** (encrypted, `DeletionProtection: true`), **Secrets Manager** secret attached via **`SecretTargetAttachment`** (auto-generated password), Security Groups for **RDS** / **Lambda** / **VPC endpoints**, **Interface** endpoints (`secretsmanager`, `logs`) + **Gateway** endpoints (`s3`, `dynamodb`). Exports **VPC id**, **private subnet id**, **Lambda SG id**, **DB secret ARN**, **DB host/port/name** for cross-stack consumption.
- [x] **Infra (api stack wiring)** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — added parameters **`RdsStackName`** + **`UseRds`**; Lambda gets `VpcConfig` (SubnetIds + SecurityGroupIds imported from `RdsStackName`), RDS-related env vars (**`USE_RDS`**, **`DB_HOST`**, **`DB_PORT`**, **`DB_NAME`**, **`DB_SECRET_ARN`**), and IAM for `ec2:*NetworkInterface*` (VPC ENIs) + `secretsmanager:GetSecretValue` scoped to the RDS secret. **Lambda timeout** raised **15s → 30s** to absorb VPC cold start + Secrets Manager fetch.
- [x] **Schema** — [`infrastructure/database/migrations/001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) — **`uuid-ossp`** extension + **`users`** / **`courses`** / **`lessons`** / **`enrollments`** tables with **`TIMESTAMPTZ`**, **`UUID PRIMARY KEY`**, **`snake_case`** columns, **`ON DELETE CASCADE`** for `lessons → courses`, and **`idx_enrollments_course_id`** for future dashboard queries.
- [x] **RDS adapters (Clean Architecture — ports unchanged)** — new `rds_repo.py` modules implementing existing repo ports:
  - [`services/course_management/rds_repo.py`](infrastructure/lambda/catalog/services/course_management/rds_repo.py) — `CourseCatalogRdsRepository` (`CourseCatalogRepositoryPort`)
  - [`services/enrollment/rds_repo.py`](infrastructure/lambda/catalog/services/enrollment/rds_repo.py) — `EnrollmentRdsRepository` (`EnrollmentRepositoryPort`); idempotent upsert via `ON CONFLICT (user_sub, course_id) DO NOTHING`
  - [`services/auth/rds_repo.py`](infrastructure/lambda/catalog/services/auth/rds_repo.py) — `UserProfileRdsRepository` (new [`services/auth/ports.py::UserProfileRepositoryPort`](infrastructure/lambda/catalog/services/auth/ports.py))
  - All use **`psycopg2`** directly with **parameterized SQL**, handle `UUID` ↔ `str`, `datetime` ↔ ISO string, and **`snake_case`** ↔ **`camelCase`** mapping; connections cached per warm Lambda container with a retry on `psycopg2.OperationalError`.
- [x] **Auth service decoupled from repo class** — [`services/auth/service.py`](infrastructure/lambda/catalog/services/auth/service.py) now depends on **`UserProfileRepositoryPort`** (structural), enabling DynamoDB / RDS swap via wiring only.
- [x] **Config + wiring** — [`config.py`](infrastructure/lambda/catalog/config.py) adds **`use_rds`** / **`db_host`** / **`db_name`** / **`db_port`** / **`db_secret_arn`** (defaults keep existing tests green). [`bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py) gains `_build_rds_connection_factory` (Secrets Manager fetch + `psycopg2.connect(sslmode='require')`) and `_build_course_repo` / `_build_enrollment_repo` / `_build_auth_repo` that return the RDS or DynamoDB adapter based on **`USE_RDS`**. `TABLE_NAME` becomes optional when `USE_RDS=true`.
- [x] **Packaging (native deps for Lambda x86_64)** — [`infrastructure/lambda/catalog/requirements.txt`](infrastructure/lambda/catalog/requirements.txt) pins **`psycopg2-binary==2.9.9`**; [`_vendor_bootstrap.py`](infrastructure/lambda/catalog/_vendor_bootstrap.py) prepends `_vendor/` to `sys.path` (imported first from [`index.py`](infrastructure/lambda/catalog/index.py)). [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) and [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1) build the Lambda zip in a temp dir and run `pip install -t _vendor --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.11 --implementation cp`. **`.gitignore`** excludes `infrastructure/lambda/catalog/_vendor/`.
- [x] **Data migration tool** — [`scripts/migrate-dynamodb-to-rds.py`](scripts/migrate-dynamodb-to-rds.py) — one-shot idempotent DynamoDB → RDS copy (`users` first for FK, then courses, lessons, enrollments) using `execute_batch` + `ON CONFLICT DO NOTHING`; supports `--dry-run`, `--batch-size`, `--log-level` and reads RDS credentials from Secrets Manager.
- [x] **IAM (GitHub deploy role)** — [`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) + [`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) — added **`RdsStackManage`**, **`Ec2VpcStackManage`**, **`SecretsManagerRdsCredentials`**, **`SecretsManagerRotationAndList`** statements so CI can deploy `StreamMyCourse-Rds-*`.
- [x] **Boundary check** — [`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py) — `bootstrap.py` added to `allowed_boto3_files`; new `allowed_psycopg2_files` (`bootstrap.py` + the three `rds_repo.py`); HTTP-import guard extended to all `rds_repo.py`. CI parity: **28 files pass**.
- [x] **Tests (TDD)** — [`tests/unit/test_config.py`](tests/unit/test_config.py) (new `TestRdsFields`), [`tests/unit/test_rds_repos.py`](tests/unit/test_rds_repos.py) (54 assertions across the three RDS adapters with a `FakeCursor`/`FakeConn` driver mock), [`tests/unit/test_bootstrap.py`](tests/unit/test_bootstrap.py) (`TestBuildAwsDepsWithRds` + `TestRdsConnectionFactory` covering Secrets Manager failure modes and `sslmode=require`). Full suite: **311 passed**, **vulture min-confidence 61 clean**.
- [x] **Docs** — new ADR [`plans/architecture/adr-0008-dynamodb-to-rds-migration.md`](plans/architecture/adr-0008-dynamodb-to-rds-migration.md); [`plans/architecture/module-map.md`](plans/architecture/module-map.md) updated for the new adapters + psycopg2/boto3 boundaries; [`tests/integration/README.md`](tests/integration/README.md) gained an **RDS cutover runbook** (deploy `rds-stack` → apply schema → run migrator dry-run/live → redeploy api stack with `UseRds=true` → integ suite → rollback by flipping `UseRds=false` and redeploying).

### Decisions (see [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md))

- **RDS** on `db.t4g.micro` (free-tier friendly) over Aurora Serverless v2 (no scale-to-zero, pricier minimum).
- **Lambda in VPC** with Gateway endpoints for S3/DynamoDB so DynamoDB repos keep working during rollback with no NAT cost.
- **Direct psycopg2** (no SQLAlchemy) — matches the thin-adapter style of the existing DynamoDB repos.
- **Feature flag `USE_RDS` off by default** — ports/contracts unchanged, rollback is a parameter flip + one `deploy.ps1 -Template api` redeploy.
- **Phase 2 groundwork, not a cost-down move.** DynamoDB is fine for MVP; RDS unlocks relational dashboards, payments/enrollments reporting, and richer joins planned in [`roadmap.md`](./roadmap.md) Phase 2.

### Deferred to operator (post-code-merge)

- Deploy `StreamMyCourse-Rds-<env>` stack; apply [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) via bastion/psql; run [`migrate-dynamodb-to-rds.py`](scripts/migrate-dynamodb-to-rds.py); flip `UseRds=true` on `StreamMyCourse-Api-<env>` when ready. Runbook: [`tests/integration/README.md`](tests/integration/README.md).

---

## 2026-05-03 — Security hardening (infra, IAM, CI, integ)

### Completed

- [x] **CloudFront response headers** — [`infrastructure/templates/edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml) — **`SpaSecurityHeadersPolicy`** (HSTS, **`nosniff`**, **`DENY`** frame options, referrer policy) attached to student + teacher default cache behaviors.
- [x] **GitHub Actions** — [`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml) / [`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml) declare **`workflow_call.secrets`**; [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) passes explicit **`secrets:`** maps (no **`secrets: inherit`** on those calls).
- [x] **GitHub deploy role (backend policy)** — [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) + [`iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) — CloudFormation scoped to **`StreamMyCourse-*`** stacks (eu-west-1 + us-east-1) with **`ValidateTemplate`** / **`ListStacks`** on **`*`**; Lambda / DynamoDB / log groups scoped to **`StreamMyCourse-*`**; API Gateway + Cognito remain regional with conditions where applicable; S3 still account-scoped for artifact + dynamic bucket names.
- [x] **Dev env docs** — [`frontend/.env.example`](frontend/.env.example) — **`VITE_API_PROXY_TARGET`** documented as required for Vite dev when using **`/api`** proxy.
- [x] **Tests** — [`tests/unit/services/course_management/test_service.py`](tests/unit/services/course_management/test_service.py) (**`set_lesson_video_if_video_key_matches`**), [`test_storage.py`](tests/unit/services/course_management/test_storage.py) (sanitized filenames); integ: [`tests/integration/test_playback_upload.py`](tests/integration/test_playback_upload.py) (**invalid video / image content types** → **400**).
- [x] **Follow-up (presign + integ)** — [`storage.py`](infrastructure/lambda/catalog/services/course_management/storage.py): removed invalid **`Conditions=`** kwargs from **`generate_presigned_url`** (boto3 does not support them; caused **500** on **`POST /upload-url`** in integ). [`test_bootstrap_edges.py`](tests/integration/test_bootstrap_edges.py): OPTIONS / GatewayResponse expectations aligned with explicit integ **`GatewayResponseAllowOrigin`** (**`http://localhost:5173`**).

---

## 2026-05-03 — Google sign-in UX, post-login return path, and header sign-out

### Completed

- [x] **Return path helper** — [`frontend/src/lib/post-login-return.ts`](frontend/src/lib/post-login-return.ts) — **`POST_LOGIN_RETURN_TO_KEY`**, **`sanitizeReturnPath`**, **`persistReturnPathBeforeHostedUi`** (same-origin relative paths; rejects **`//`**, **`\`**, and **`/login`**); Vitest coverage in [`frontend/src/lib/post-login-return.test.ts`](frontend/src/lib/post-login-return.test.ts).
- [x] **`PostLoginRedirect`** — [`frontend/src/components/auth/PostLoginRedirect.tsx`](frontend/src/components/auth/PostLoginRedirect.tsx) — after **`authStatus === 'authenticated'`**, restores **`sessionStorage`** target via **`navigate(..., { replace: true })`** and clears storage once the router location matches (safe with React StrictMode); mounted from [`frontend/src/student-app/App.tsx`](frontend/src/student-app/App.tsx), [`frontend/src/teacher-app/App.tsx`](frontend/src/teacher-app/App.tsx); tests in [`frontend/src/components/auth/PostLoginRedirect.dom.test.tsx`](frontend/src/components/auth/PostLoginRedirect.dom.test.tsx).
- [x] **`SignIn.tsx`** — [`frontend/src/components/auth/SignIn.tsx`](frontend/src/components/auth/SignIn.tsx) — calls **`persistReturnPathBeforeHostedUi`** before **`signInWithRedirect`**; refreshed card layout + Google mark; tests extended in [`frontend/src/components/auth/SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx).
- [x] **`StudentLoginPage`** — [`frontend/src/pages/StudentLoginPage.tsx`](frontend/src/pages/StudentLoginPage.tsx) — **`Navigate to="/"`** when already authenticated (fixes blank signed-in **`/login`**); tests in [`frontend/src/pages/StudentLoginPage.dom.test.tsx`](frontend/src/pages/StudentLoginPage.dom.test.tsx).
- [x] **Marketing `Header`** — *(removed 2026-05-04 — Option B; student shell uses [`StudentHeader`](frontend/src/student-app/StudentHeader.tsx) only; coverage in [`StudentHeader.dom.test.tsx`](frontend/src/student-app/StudentHeader.dom.test.tsx).)* Previously **`Header.tsx`** + **`Header.dom.test.tsx`** under **`frontend/src/components/layout/`**.
- [x] **`main.tsx`** (removed 2026-05-04) — legacy combined entry; **`student-main.tsx`** / **`teacher-main.tsx`** now wrap **`AuthenticatorProvider`** + **`BrowserRouter`** for each SPA.

---

## 2026-05-03 — Custom Google-only SignIn (Amplify Authenticator UI removed)

### Completed

- [x] **`SignIn.tsx`** ([`frontend/src/components/auth/SignIn.tsx`](frontend/src/components/auth/SignIn.tsx)) — **`Continue with Google`** button → **`signInWithRedirect({ provider: 'Google' })`** (**`aws-amplify/auth`**); **`useAuthenticator`** **`authStatus`** gates **`children`**; **`configuring`** shows **Signing in…** (**`GOOGLE_SIGN_IN_LABEL`** exported for tests).
- [x] **`AuthenticatorProvider`** — [`frontend/src/teacher-main.tsx`](frontend/src/teacher-main.tsx) wraps **BrowserRouter** (parity with [`student-main.tsx`](frontend/src/student-main.tsx)); removed **`@aws-amplify/ui-react/styles.css`** imports from SPA entrypoints (hooks-only **`useAuthenticator`**).
- [x] **`TeacherRoleGate`** ([`frontend/src/components/auth/TeacherRoleGate.tsx`](frontend/src/components/auth/TeacherRoleGate.tsx)) — gate on **`authStatus === 'authenticated'`** instead of **`route`**.
- [x] **Removed** Amplify **`Authenticator`** shell hacks: deleted [`frontend/src/components/auth/sign-in-federated-shell.css`](frontend/src/components/auth/sign-in-federated-shell.css) and [`frontend/src/components/auth/signInAmplifyUi.ts`](frontend/src/components/auth/signInAmplifyUi.ts).
- [x] **Tests** — [`frontend/src/components/auth/SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx) (**`vi.mock('aws-amplify/auth')`**, **`AuthenticatorProvider`** wrapper, **`fireEvent.click`**).

---

## 2026-05-03 — Google-federation-only Cognito (template, deploy gates, SignIn shell)

### Completed

- [x] **[`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml)** — Removed **`Conditions` / `HasGoogle`**; **`GoogleIdentityProvider`** always; student/teacher **`SupportedIdentityProviders: [Google]`**; **`GoogleClientId` / `GoogleClientSecret`** required (**`MinLength: 1`**); app clients **`ExplicitAuthFlows`** → **`ALLOW_REFRESH_TOKEN_AUTH`** only (OAuth code + refresh).
- [x] **[`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)** — **`Require Google OAuth`** step before **Deploy auth** (dev + prod); **`parameter-overrides`** always passes **`GoogleClientId`** / **`GoogleClientSecret`** from secrets (no **`${VAR:+…}`** omission).
- [x] **[`infrastructure/deploy.ps1`](infrastructure/deploy.ps1)** — **`-Template auth`** fails fast without **`GoogleClientId`** and **`GoogleClientSecret`**; both always included in overrides.
- [x] **Frontend** — **`SignIn.tsx`** + Authenticator shell (later **superseded** by **Custom Google-only SignIn** entry below: `signInWithRedirect`, no `<Authenticator>`); originally shipped with `signInAmplifyUi.ts` + `sign-in-federated-shell.css`. Call sites: [`StudentLoginPage.tsx`](frontend/src/pages/StudentLoginPage.tsx), [`StudentLessonAuth.tsx`](frontend/src/components/auth/StudentLessonAuth.tsx), [`teacher-app/App.tsx`](frontend/src/teacher-app/App.tsx); removed **`frontend/src/styles/federated-only-authenticator.css`** global import + file.
- [x] **Tests** — [`frontend/src/components/auth/SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx) (**Testing Library** + **`@vitest-environment jsdom`**); devDependencies **`@testing-library/react`**, **`jsdom`**.
- [x] **Docs** — [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md), [`design.md`](design.md), [`roadmap.md`](roadmap.md) — no **`HasGoogle`** / COGNITO-bootstrap path for this template.

---

## 2026-05-03 — Documentation: post-MVP stance and engineering quality bar

### Completed

- [x] **`design.md`** — Header clarifies **MVP contract is shipped**; ongoing evolution and quality expectations point to roadmap and Implementation History (no change to MVP requirement tables unless a future RFC updates them).
- [x] **`roadmap.md`** — Status line set to **post-MVP evolution**; explicit **engineering bar**: prefer **supported auth UI patterns** over brittle **CSS masking** (later superseded by **Custom Google-only SignIn** — no CSS hiding; see history entry same day).
- [x] **`AGENTS.md`** — Index note for contributors: post-MVP **clean code / no hacks** default.

---

## 2026-05-03 — Strict SPA Cognito runtime (Hosted UI domain; no Amplify native email fallback)

### Completed

- [x] **`frontend/src/lib/auth.ts`** — Amplify **`loginWith.oauth`** only; **`isAuthConfigured()`** requires **pool id**, **client id**, and **`VITE_COGNITO_DOMAIN`** trimmed non-empty (parity with **`scripts/check-cognito-spa-env.mjs`**).
- [x] **`frontend/src/lib/cognito-hosted-ui-env.ts`** — Pure predicate **`cognitoHostedUiEnvComplete`**, exercised by **`frontend/src/lib/cognito-hosted-ui-env.test.ts`** (**Vitest**).
- [x] **`frontend/package.json`** — **`npm run test`** (**`vitest run`**); **`frontend/vitest.config.ts`** (**Node** environment).
- [x] **`.github/workflows/ci.yml`** — **Frontend checks** runs **`npm run test`** after **`npm run build:all`**.
- [x] **Copy / ops / contract** — [`frontend/.env.example`](frontend/.env.example); [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md) **Deprecated workflows** + anchor link to clean slate; [`design.md`](design.md), [`roadmap.md`](roadmap.md) runtime parity wording.

---

## 2026-05-03 — Google-only federated auth (student + teacher SPAs)

### Completed

- [x] **[`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml)** — **(Superseded by unconditional Google-only template same day — see history entry *Google-federation-only Cognito*.)** Earlier revision used **`HasGoogle`** so clients could stay **`COGNITO`**-only without Google secrets.
- [x] **[`scripts/check-cognito-spa-env.mjs`](scripts/check-cognito-spa-env.mjs)** + **[`frontend/package.json`](frontend/package.json)** **`prebuild:student`** / **`prebuild:teacher`** — build fails if pool id + client id are set without **`VITE_COGNITO_DOMAIN`**; loads **`frontend/.env*`** like Vite production.
- [x] **[`tests/unit/test_cognito_spa_env_contract.py`](tests/unit/test_cognito_spa_env_contract.py)** — subprocess contract tests for the checker.
- [x] **Frontend** — [`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts) Hosted UI **`loginWith.oauth`** for Google flows; **`hideSignUp`** + Google on login surfaces — later replaced by **[`SignIn.tsx`](frontend/src/components/auth/SignIn.tsx)** shell + scoped CSS; strict domain + OAuth-only SPA config (see **`2026-05-03 — Strict SPA Cognito runtime`** above).
- [x] **Removed** `scripts/create-first-admin.py` (native bootstrap incompatible with Google-only public clients).
- [x] **Runbook** — [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md) pre-launch wipe (DynamoDB → S3 → Cognito order), Google Cloud / GitHub secrets, smoke verification, rollback, future IdPs.
- [x] **Contract docs** — [`design.md`](design.md), [`roadmap.md`](roadmap.md) MVP baseline / §13 auth row.

---

## 2026-05-03 — CD: unified edge hosting (`StreamMyCourse-EdgeHosting-*`) and required Cognito

### Completed

- [x] **[`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml)** — CloudFormation bootstrap for GitHub OIDC deploy role + inline policies (manual `deploy-github-iam-stack` scripts; **not** wired into CI/CD). JSON policy files remain mirrors for review / `apply-github-deploy-role-policies` path.
- [x] **[`infrastructure/templates/edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml)** — Single **`us-east-1`** stack: ACM + student + teacher S3/OAC/CloudFront/Route 53; both distributions **`!Ref Certificate`**.
- [x] **[`scripts/deploy-edge.sh`](scripts/deploy-edge.sh)** — One **`aws cloudformation deploy`** for **`StreamMyCourse-EdgeHosting-{env}`**; env **`ROUTE53_HOSTED_ZONE_ID`**, **`STUDENT_WEB_DOMAIN`**, **`TEACHER_WEB_DOMAIN`**, optional **`WEB_CERT_DOMAIN`** / **`WEB_CERT_SANS`**.
- [x] **[`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)** — **`deploy-edge-*`** job graph; edge steps run unified script. Dev **`deploy-backend-*`** / **`deploy-web-*`** / **`deploy-teacher-web-*`** **`needs`** **`deploy-edge-dev`** after integ tests; **prod** app jobs **`needs`** full dev column + **`deploy-edge-prod`**; **auth** fail-fast if **`COGNITO_DOMAIN_PREFIX`** unset.
- [x] **[`.github/workflows/deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml)** / **[`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml)** — **`AWS_REGION: us-east-1`**; stack **`StreamMyCourse-EdgeHosting-${env}`**; outputs **`StudentBucketName`**, **`StudentDistributionId`**, **`StudentSiteUrl`** / teacher equivalents.
- [x] **[`infrastructure/iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json)** — **`DescribeStacks`** ARNs for **`StreamMyCourse-EdgeHosting-*`** (**`us-east-1`**).
- [x] **[`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json)** — *(unchanged this session; already had ACM / Route53 / CloudFront for edge.)*
- [x] **[`infrastructure/deploy.ps1`](infrastructure/deploy.ps1)** — **`-Template edge-hosting`**, **`TeacherDomainName`**, optional **`CertPrimaryDomain`**.
- [x] **[`.github/workflows/ci.yml`](.github/workflows/ci.yml)** — Parse **`edge-hosting-stack.yaml`**; **`workflow-lint`** unchanged.
- [x] **[`tests/unit/test_deploy_edge_script.py`](tests/unit/test_deploy_edge_script.py)** — **`bash -n`** + single-stack **`us-east-1`** contract.
- [x] Docs: [`infrastructure/docs/edge-hosting-migration.md`](infrastructure/docs/edge-hosting-migration.md), [`plans/architecture/adr-0007-web-hosting.md`](plans/architecture/adr-0007-web-hosting.md) addendum, [`design.md`](design.md), [`roadmap.md`](roadmap.md), [`AGENTS.md`](AGENTS.md), [`infrastructure/README.md`](infrastructure/README.md), [`admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md).
- [x] **Prod app deploy gate** — **`deploy-backend-prod`**, **`deploy-web-prod`**, **`deploy-teacher-web-prod`** **`needs`** **`deploy-backend-integ`**, **`integ-tests`**, **`deploy-edge-dev`**, **`deploy-backend-dev`**, **`deploy-web-dev`**, **`deploy-teacher-web-dev`**, and **`deploy-edge-prod`** so prod never ships on prod edge alone. **`deploy-edge-prod`** unchanged: after **`integ-tests`** + **`deploy-edge-dev`** only.
- [x] **OIDC CloudFormation type** — [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) uses **`AWS::IAM::OIDCProvider`** (not `OIDCIdentityProvider`). **[`scripts/deploy-github-iam-stack`](scripts/deploy-github-iam-stack.sh)** / [`.ps1`](scripts/deploy-github-iam-stack.ps1) exit non-zero when **`aws cloudformation deploy`** fails.
- [x] **README (GitHub OIDC)** — documents **one** `token.actions.githubusercontent.com` provider per account, **`ExistingGithubOidcProviderArn`** for brownfield, and that **stack delete** does not remove a pre-existing OIDC registration.
- [x] **[`.cursor/skills/watch-ci-after-push/SKILL.md`](.cursor/skills/watch-ci-after-push/SKILL.md)** — after a green **CI** run on `main`, resolve and **`gh run watch`** the **Deploy** workflow run matching **`headSha`** ([`deploy-backend.yml`](.github/workflows/deploy-backend.yml)).

---

## 2026-05-03 — EdgeHosting migration completed (retire legacy Web/TeacherWeb/Cert)

### Completed

- [x] **Retired legacy stacks (eu-west-1):** deleted `StreamMyCourse-Web-{dev|prod}` and `StreamMyCourse-TeacherWeb-{dev|prod}` after emptying **versioned** S3 buckets (must delete all versions + delete markers before stack deletion succeeds).
- [x] **Retired legacy stacks (us-east-1):** deleted `StreamMyCourse-Cert-{dev|prod}` after cutover succeeded.
- [x] **Edge aliases enabled by default:** removed `EDGE_ATTACH_CF_ALIASES=false` overrides in **[`deploy-backend.yml`](.github/workflows/deploy-backend.yml)** so `StreamMyCourse-EdgeHosting-{env}` attaches custom domain aliases and manages Route 53 records.
- [x] **Removed legacy IaC + workflows:** deleted `infrastructure/templates/{web-stack,teacher-web-stack,web-cert-stack}.yaml` and the manual `.github/workflows/deploy-web.yml` / `deploy-teacher-web.yml` entrypoints; SPA deploys run only via **[`deploy-backend.yml`](.github/workflows/deploy-backend.yml)** using the reusable workflows.
- [x] **IAM narrowed to EdgeHosting only:** updated **[`infrastructure/iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json)** and **[`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml)** to target `StreamMyCourse-EdgeHosting-*` and the `us-east-1` student/teacher site buckets.

### Notes

- DNS may briefly return **NXDOMAIN** during cutover due to negative caching; authoritative Route 53 name servers resolve immediately once records exist.

## 2026-04-30 — Project Initialization

### ✅ Completed

#### Design & Planning
- [x] Created `design.md` — MVP architecture and requirements
- [x] Created `roadmap.md` — Full future vision and phases
- [x] Locked MVP design decisions (8 questions answered)
  - Auth: AWS Cognito with Google OAuth
  - Lambda runtime: Python
  - Admin: DynamoDB Console for MVP
  - Upload limits: 10GB per file
  - Local testing: Yes with AWS dev credentials
  - Course status: Draft → Published (2 states)

#### MVP Scope Change
- [x] Re-scoped MVP to frontend-first demo with **no auth** and **MP4 playback**
- [x] MVP backend will be a single API-invoked Lambda behind API Gateway (no triggers)

#### AWS Infrastructure Setup
- [x] Installed AWS CLI v2.34.39
- [x] Configured AWS credentials (eu-west-1)
- [x] Verified connectivity: `aws sts get-caller-identity`
- [x] Created CloudFormation dummy stack (`streammycourse-dummy`)
  - S3 bucket: `streammycourse-test-dev-[REDACTED]`
  - DynamoDB table: `TestTable-dev`
  - IAM role: `StreamMyCourse-LambdaRole-dev`

#### Version Control
- [x] Initialized Git repository
- [x] Created `.gitignore` (Node, Python, AWS, IDE)
- [x] Pushed to GitHub: `https://github.com/Ahmed-Wesam/StreamMyCourse`
- [x] Set `main` as default branch (deleted `master`)

#### Infrastructure as Code
- [x] Created `infrastructure/` directory structure
- [x] Created `infrastructure/templates/dummy-stack.yaml`
- [x] Created `infrastructure/deploy.ps1` deployment script
- [x] Created `infrastructure/README.md` documentation

#### Frontend Development
- [x] Scaffolded React with Vite (React + TypeScript template)
- [x] Installed and configured Tailwind CSS v3
- [x] Installed React dependencies (react, react-dom, types)
- [x] Created App.tsx with basic landing page
- [x] Configured Tailwind directives in style.css
- [x] Added React Router
- [x] Implemented pages: course catalog, course detail, lesson player (MP4)
- [x] Added API client (`VITE_API_BASE_URL` required at runtime; see `frontend/.env.example`)
- [x] Dev server running at http://localhost:5173/
- [x] Committed frontend code to git

### ✅ Completed (MVP Infrastructure)
- [x] Created minimal Lambda API (courses/lessons/playback/upload-url)
- [x] Created CloudFormation template for API Gateway + Lambda (no event sources)
- [x] Deployed S3 bucket for video hosting with public access
- [x] Connected frontend to AWS API (VITE_API_BASE_URL configured)
- [x] Implemented instructor upload flow with presigned S3 URLs

---

## 2026-05-01 — MVP Completion & Cleanup

### ✅ Completed

#### Infrastructure & Backend
- [x] **Fixed CORS issues** on `/upload-url` endpoint (OPTIONS method + echo Origin)
- [x] **Added S3 bucket CORS** for browser PUT uploads via presigned URLs
- [x] **Refactored Lambda code** out of inline YAML into `infrastructure/lambda/catalog/index.py`
- [x] **Updated deployment** to package Lambda zip and upload to S3 before CloudFormation deploy
- [x] **Increased Lambda resources** (timeout: 15s, memory: 512MB) for stable presign generation
- [x] **Hardened request parsing** for `/upload-url` (base64, quoted JSON, simple key:value)
- [x] **Tightened IAM permissions** (initially scoped `s3:PutObject` to `${bucket}/uploads/*`; later **2026-05-04** widened to `${bucket}/*` for course-scoped keys—see current `api-stack.yaml`)
- [x] **Added configurable CORS** via `ALLOWED_ORIGINS` environment variable
- [x] **Deleted dummy-stack.yaml** (cleanup unused test resources)

#### Frontend
- [x] **Improved UI** on all pages (CourseCatalog, CourseDetail, LessonPlayer)
- [x] **Added skeleton loading** states and better error handling
- [x] **Removed console.log leaks** from instructor upload UI (security cleanup; page later replaced by course management flow)
- [x] **Fixed Tailwind CSS loading** (added missing import to main.tsx)

#### Security Audit
- [x] IAM: Removed overly broad S3 permissions, scoped to specific bucket/prefix
- [x] CORS: Origin validation with configurable allowlist
- [x] Error handling: No sensitive data in error responses or logs
- [x] Frontend: No console logs leaking to user

### 📋 Next priority (superseded)

Superseded by the **2026-05-01 (later)** section below (DynamoDB + instructor flows shipped). Use that section’s “Next priority (revised)” list.

### 📋 Later (Optional)
- [ ] User authentication (Cognito or OAuth)
- [ ] Video transcoding (MediaConvert)
- [ ] Progress tracking for students
- [ ] Reviews & ratings
- [ ] Analytics dashboard

### 📝 Notes
- Region: `eu-west-1` (Ireland)
- Account: `[REDACTED]`
- Video stacks: **`StreamMyCourse-Video-dev`** / **`StreamMyCourse-Video-prod`** (bucket names from stack outputs; legacy `streammycourse-video` removed 2026-05-02)
- API endpoint: `https://qstuxlbcp4.execute-api.eu-west-1.amazonaws.com/dev`
- **Current status:** MVP fully functional (browse, watch, instructor course/lesson management, publish, presigned upload)
- **DRM:** Deferred (Phase 2)

---

## 2026-05-01 (later) — DynamoDB, modular Lambda, CORS hardening, CI guardrails

### ✅ Completed

#### Data & API
- [x] **DynamoDB catalog table** in `api-stack.yaml` (`StreamMyCourse-Catalog-{env}`); Lambda `TABLE_NAME` wired
- [x] **Course CRUD + publish**, **lesson CRUD**, **playback** (requires `videoStatus=ready`), **`POST /upload-url`** with `courseId` + `lessonId`
- [x] **`PUT /courses/{id}/lessons/{lid}/video-ready`** so client can mark video ready after S3 upload (enables publish workflow)
- [x] **Strict JSON body parsing** (no “repair malformed JSON”); validation errors return 400

#### Architecture (modular monolith in one Lambda)
- [x] **Layered package:** `services/course_management/` (controller → service → repo/storage), **`Protocol` ports** (`ports.py`), domain **`models.py`**, API **`contracts.py`** (TypedDict DTOs at controller boundary)
- [x] **Composition root:** [`bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py); thin [`index.py`](infrastructure/lambda/catalog/index.py) (503 `catalog_unconfigured` when `TABLE_NAME` unset; no mock catalog)
- [x] Stub bounded context [`services/auth/`](infrastructure/lambda/catalog/services/auth/) for future work
- [x] **Cursor rule** [`.cursor/rules/clean-architecture-boundaries.mdc`](.cursor/rules/clean-architecture-boundaries.mdc) documenting layer rules

#### CORS & API Gateway
- [x] **`CorsAllowOrigin` CloudFormation parameter** → Lambda `ALLOWED_ORIGINS`
- [x] **GatewayResponses** (`DEFAULT_4XX`, `DEFAULT_5XX`) so CORS headers appear on gateway error responses, not only Lambda success paths
- [x] **Lesson routes** on API Gateway aligned with Lambda (POST/PUT/DELETE lessons + OPTIONS + `video-ready`)

#### Frontend
- [x] **Instructor dashboard** (`/instructor`) and **course management** (`/instructor/courses/:id`) — create course, lessons, upload, publish, mark video ready after upload
- [x] **Removed** standalone `InstructorUploadPage` and `/instructor/upload` route; catalog links point to `/instructor`
- [x] **Vite dev proxy** ([`frontend/vite.student.config.ts`](frontend/vite.student.config.ts) / [`frontend/vite.teacher.config.ts`](frontend/vite.teacher.config.ts)) + `.env` pattern for local API without CORS friction

#### CI & quality
- [x] **GitHub Actions** [`.github/workflows/ci.yml`](.github/workflows/ci.yml): frontend build, Lambda compile-all, CloudFormation YAML parse
- [x] **Import boundary script** [`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py) (e.g. `boto3` only in adapters; no `course_management` ↔ `auth` cross-imports)

#### Documentation (repo)
- [x] **Module map + ADRs** under [`plans/architecture/`](plans/architecture/) (single-table Dynamo, versioning, trust model, future auth, CI enforcement, data access evolution)

#### Deployment note
- [x] Lambda code updates: use **unique S3 artifact key** or `aws lambda update-function-code` when CloudFormation reports “no changes” but code changed

### 📋 Next priority (revised)

**Option A — CloudFront (video)**  
CDN for MP4; tighten S3 direct access when ready.

**Option B — Frontend hosting**  
Build + deploy SPA to S3; optional CloudFront + custom domain.

**Option C — Auth**  
Cognito / API Gateway authorizer; implement `services/auth` boundary per ADR.

### 📋 Later (unchanged themes)
- [ ] Progress, reviews, analytics, transcoding, etc. (see `roadmap.md`)

---

## 2026-05-02 — No mock catalog; API URL required; static analysis in CI

### Completed

- [x] **Lambda:** Removed `mock_router.py`; catalog requires `TABLE_NAME` — handler returns **503** `catalog_unconfigured` when unset (OPTIONS unchanged); removed dead `mock_mode` path from controller
- [x] **Frontend:** Removed embedded mock data in `api.ts`; **`VITE_API_BASE_URL` required** at runtime; added [`frontend/.env.example`](frontend/.env.example)
- [x] **Instructor dashboard:** Lesson counts from **`listLessons`** per course (parallel fetch)
- [x] **CI / tooling:** ESLint (incl. `complexity` warn), Knip, Vulture (blocking), Radon `cc` (informational); updated [`design.md`](design.md), [`AGENTS.md`](AGENTS.md), module map, DynamoDB plan notes

---

## 2026-05-02 — Frontend Hosting (Priority 2 from design.md §13)

### Completed

#### Infrastructure
- [x] **ACM certificate stack** ([`infrastructure/templates/web-cert-stack.yaml`](infrastructure/templates/web-cert-stack.yaml)): DNS-validated cert in **us-east-1** (CloudFront requirement)
- [x] **Web hosting stack** ([`infrastructure/templates/web-stack.yaml`](infrastructure/templates/web-stack.yaml)): Private S3 bucket + CloudFront OAC + Route 53 alias records
  - SPA error mappings: 403/404 → `/index.html` (200) for client-side routing
  - Cache policies: `CachingOptimized` for assets, custom headers for `index.html` (no-cache)
  - PriceClass 100 (North America/Europe), TLS 1.2+, HTTP/2+HTTP/3, IPv6
- [x] **Deploy script** ([`infrastructure/deploy.ps1`](infrastructure/deploy.ps1)): Extended with `web` and `web-cert` templates
  - Cross-region handling (us-east-1 for ACM, eu-west-1 for web)
  - SPA build with `VITE_API_BASE_URL` injection
  - S3 sync with cache-control headers (immutable for assets, no-cache for index.html)
  - CloudFront invalidation after deploy

#### API CORS fix
- [x] **GatewayResponse parameter separation** ([`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml))
  - `CorsAllowOrigin`: CSV supported for Lambda success responses (e.g., "https://app.example.com,https://dev.example.com,http://localhost:5173")
  - `GatewayResponseAllowOrigin`: Single value for API Gateway error responses (must be valid HTTP header)

#### CI/CD
- [x] **Deploy workflow** ([`.github/workflows/deploy-web.yml`](.github/workflows/deploy-web.yml)): OIDC-based deployment
  - Triggers on push to `main` or manual (`workflow_dispatch`)
  - Reads stack outputs (bucket, distribution ID)
  - Builds with `VITE_API_BASE_URL` from secrets
  - Syncs to S3 with proper cache headers
  - Invalidates CloudFront distribution

#### Documentation
- [x] Updated [`design.md`](design.md) §10 with web hosting deployment steps and CORS guidance
- [x] Updated [`AGENTS.md`](AGENTS.md) code anchors to include web stacks and deploy workflow

### Deployment notes
- Requires Route 53 domain registration (manual, one-time)
- Subdomains per environment: e.g., `dev.yourdomain.com`, `app.yourdomain.com`
- GitHub repository secrets needed: `AWS_DEPLOY_ROLE_ARN`, `VITE_API_BASE_URL` (per env)

---

## 2026-05-02 — Teacher web prod mirror + CI invalidation permissions

### ✅ Completed

#### Teacher SPA build correctness
- [x] Fixed teacher production build to use `frontend/teacher.html` → `frontend/src/teacher-main.tsx` (was implicitly building the student entry via default `index.html`). **Student build** later gained explicit **`student.html`** input + rename to **`dist/student/index.html`** when root **`index.html`** / legacy **`App.tsx`** were removed (2026-05-04).
- [x] Teacher build now emits `dist/teacher/index.html` (CloudFront `DefaultRootObject`) by renaming the emitted `teacher.html` in the build output (see `frontend/vite.teacher.config.ts`).
- [x] Teacher header “View Student Site” points to `VITE_STUDENT_SITE_URL` (CI sets prod to `https://app.streammycourse.click`) with a safe fallback for local/dev.

#### Prod deployment + CORS
- [x] Deployed updated teacher SPA to prod S3 bucket (`StreamMyCourse-TeacherWeb-prod` outputs) and invalidated CloudFront cache.
- [x] Updated prod API Lambda `StreamMyCourse-Catalog-prod` `ALLOWED_ORIGINS` to include `https://teach.streammycourse.click` so the teacher site can call the API.

#### CI/CD permission fix
- [x] Fixed GitHub Actions OIDC deploy role permissions: `infrastructure/iam-policy-github-deploy-web.json` now allows `cloudfront:CreateInvalidation` on the **teacher** distributions and S3 access to the teacher site buckets, in addition to the student site.
- [x] This unblocked `.github/workflows/deploy-teacher-web-reusable.yml` invalidation step (previously `AccessDenied` on teacher distribution).

---

## 2026-05-02 — Cognito auth (optional) + integration runner + login UX fixes

### ✅ Completed

#### Cognito + API (optional enforcement)
- [x] Added Cognito auth stack template [`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml); **deploy** is the **Deploy** workflow’s auth step before [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) when `COGNITO_DOMAIN_PREFIX` is set on the matching GitHub Environment (**`dev`** / **`prod`**) per job ([`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)).
- [x] API Gateway authorizer wiring in [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) gated by `CognitoUserPoolArn` (empty keeps API open).
- [x] Lambda auth bounded context: [`infrastructure/lambda/catalog/services/auth/`](infrastructure/lambda/catalog/services/auth/) with `GET /users/me` profile creation/lookup in DynamoDB (`USER#<sub>`).
- [x] Course authorization when enabled: teacher/admin role checks + course ownership via `createdBy` in `services/course_management`.
- [x] Admin bootstrap + runbook: ~~`scripts/create-first-admin.py`~~ (removed 2026-05-03 in favor of Google-only break-glass); [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md).

#### Frontend auth (Amplify)
- [x] Added Amplify configuration + helpers in [`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts).
- [x] Added JWT attachment to API requests and `/users/me` client call in [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts).
- [x] Student + teacher auth UI / route gating: `frontend/src/components/auth/*`, [`frontend/src/pages/StudentLoginPage.tsx`](frontend/src/pages/StudentLoginPage.tsx), student/teacher headers.

#### Local dev + integration testing
- [x] Added PowerShell runner [`scripts/run-integ.ps1`](scripts/run-integ.ps1) to deploy integ backend, export `INTEG_*` env vars, and run `python -m pytest tests/integration`.
- [x] Added auth probes integration tests: [`tests/integration/test_auth_gateway.py`](tests/integration/test_auth_gateway.py).
- [x] Deployment correctness: `infrastructure/deploy.ps1` now strips `__pycache__`/`*.pyc` and includes a zip content hash in the Lambda artifact key so CloudFormation updates code even without a new git commit.
- [x] Fixed public header “Log In” routing to `/login` and ensured the dev entrypoint supports `/login` without redirect loops.
- [x] Note: Early CloudFormation deploys failed with `AWS::EarlyValidation::PropertyValidation` until the user pool custom attribute was corrected to `custom:role` in the template; user pool display name is `${AWS::StackName}-users` to avoid clashing with any legacy manually created pools.

## 2026-05-02 (session) — Backend CI, S3 presign hardening, legacy stack removal, `update_docs` skill

### CI / deploy
- [x] **[`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)** — OIDC deploy of video + API (`scripts/deploy-backend.sh`); **dev** then **prod** (`needs`); every push to `main`; concurrency **queues** (`cancel-in-progress: false`)
- [x] **[`deploy-web.yml`](.github/workflows/deploy-web.yml)** + **[`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml)** — SPA **dev** then **prod** on `main`; manual dispatch (both / dev / prod-only)
- [x] **Unique Lambda artifact keys** — `catalog-{env}-{gitSha12}.zip` in [`deploy-backend.sh`](scripts/deploy-backend.sh) and [`deploy.ps1`](infrastructure/deploy.ps1) so CloudFormation updates Lambda each run
- [x] **IAM:** inline policy **`StreamMyCourseGitHubDeployBackend`** from [`iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) on OIDC role (same `AWS_DEPLOY_ROLE_ARN`)

### S3 / Lambda / frontend
- [x] **Presigned URLs:** SigV4 + regional S3 endpoint in [`storage.py`](infrastructure/lambda/catalog/services/course_management/storage.py); `presign_get` for playback; **`s3:GetObject`** on API Lambda role; video bucket CORS (origins + range headers)
- [x] **Upload UI:** stable `Content-Type` for presign match ([`CourseManagement.tsx`](frontend/src/pages/CourseManagement.tsx)); empty `contentType` → `video/mp4` in controller

### AWS cleanup (CLI)
- [x] Deleted **`streammycourse-dummy`** (emptied `streammycourse-test-dev-[REDACTED]` first)
- [x] Deleted legacy **`streammycourse-video`** stack and bucket contents (test data)

### Docs / tooling
- [x] [`infrastructure/README.md`](infrastructure/README.md) — removed dummy-stack quick start; stack deletion notes; typo fix
- [x] **Cursor skill** [`.cursor/skills/update-docs/SKILL.md`](.cursor/skills/update-docs/SKILL.md) — invoke **`/update_docs`** to refresh `design.md`, `roadmap.md`, `ImplementationHistory.md` from session work

---

## 2026-05-02 — Lesson SK refactor + Integration test environment

### Lesson SK refactor (data-loss bug fix)
- [x] **Bug:** [`repo.create_lesson`](infrastructure/lambda/catalog/services/course_management/repo.py) used `next_order = len(existing) + 1`, so deleting a middle lesson and creating a new one silently overwrote an existing lesson via `LESSON#{order:03d}` SK collision.
- [x] **Fix:** SK is now `LESSON#{lesson_id}` (UUID-based, collision-free). `order` is stored as an explicit attribute. `next_order = max(existing.order, default=0) + 1`. `list_lessons` sorts by `order` after query. `_format_lesson` keeps a backward-compat path for any legacy `LESSON#NNN` rows.
- [x] **API surface change:** `update_lesson_title`, `delete_lesson`, `set_lesson_video`, `set_lesson_video_status` now key by `lesson_id` instead of `order`.
- [x] **New repo method** `set_lesson_orders(course_id, orders)` for bulk reorder; aliases reserved word `order` via `ExpressionAttributeNames`. Not yet wired through controller.

### Integration test environment ('integ' as a third backend stack)
- [x] **Decision:** dedicated integ AWS environment (full backend stack with its own DDB + S3) deployed on every push; pytest hits the integ API over HTTPS; prod gates on tests passing.
- [x] **Infra wiring:** `Environment=integ` added to [`api-stack.yaml`](infrastructure/templates/api-stack.yaml) and [`video-stack.yaml`](infrastructure/templates/video-stack.yaml) `AllowedValues`; [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) and [`infrastructure/deploy-environment.ps1`](infrastructure/deploy-environment.ps1) accept `integ` and provision `StreamMyCourse-Api-integ` + `StreamMyCourse-Video-integ` with wildcard CORS.
- [x] **CI flow** in [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml): **integ → integ-tests → dev → prod**, each step gated on the prior. Dispatch input `full` (default) or `integ-only`.
- [x] **integ-tests job:** sets up Python 3.11, installs `tests/integration/requirements.txt`, resolves `INTEG_API_BASE_URL` / `INTEG_VIDEO_BUCKET` from CFN outputs, runs `pytest --junitxml=results.xml`, uploads the JUnit XML as an artifact, writes pass/fail to `$GITHUB_STEP_SUMMARY`.

### Test harness (HTTP via httpx + pytest)
- [x] **Layout:** [`tests/integration/`](tests/integration/) at repo root (outside the Lambda zip; not scanned by `check_lambda_boundaries.py` or vulture).
- [x] **Fixtures** in [`conftest.py`](tests/integration/conftest.py): `api_base_url`, `http_client`, `api`, `course_factory`, `lesson_factory`. Course teardown deletes via `DELETE /courses/{id}`; lesson cleanup is implicit (course delete cascades).
- [x] **Helpers:** [`api.py`](tests/integration/helpers/api.py) (typed httpx wrapper per endpoint), [`factories.py`](tests/integration/helpers/factories.py) (UUID-prefixed titles), [`cleanup.py`](tests/integration/helpers/cleanup.py) (boto3 truncate + S3 sweep).
- [x] **Session-end safety net:** `pytest_sessionfinish` scans the integ DDB for test-prefixed leftovers and empties **all objects** in the integ video bucket; logs to `$GITHUB_STEP_SUMMARY` but **never fails** the job.

### Test scenarios (28 collected)
- [x] **Smoke** ([`test_smoke.py`](tests/integration/test_smoke.py)) — harness wiring + cleanup proof.
- [x] **S1 edges** ([`test_bootstrap_edges.py`](tests/integration/test_bootstrap_edges.py)) — OPTIONS preflight, origin echo, 404 unknown route/method, 400 malformed JSON / array body, 400 missing required `courseId`/`lessonId` on `/upload-url`.
- [x] **S2 courses** ([`test_courses.py`](tests/integration/test_courses.py)) — CRUD + draft-not-in-public-catalog filter + delete cascades to lessons.
- [x] **S3 publish** ([`test_publish.py`](tests/integration/test_publish.py)) — publish-without-ready-lesson 400, video-ready-without-upload 400, full publish flow appears in catalog.
- [x] **S4 playback / upload** ([`test_playback_upload.py`](tests/integration/test_playback_upload.py)) — playback gating, presigned URL shape, full S3 round-trip (`@pytest.mark.slow`) verifying PUT then GET via presigned URLs.
- [x] **S5 lesson ordering regression** ([`test_lesson_ordering.py`](tests/integration/test_lesson_ordering.py)) — delete-middle-then-create no longer collides; `list_lessons` returns sorted by `order`.

### Static-check coverage in PR/push CI
- [x] [`/.github/workflows/ci.yml`](.github/workflows/ci.yml): new `integ-tests-static` job — installs test deps, py-compiles `tests/integration/**/*.py`, and runs `pytest --collect-only` to surface import errors before they hit a real deploy. `cloudformation` job now also parses `video-stack.yaml`.

---

## 2026-05-02 — Lambda unit-test suite + CI gate

### Test harness
- [x] **Layout:** [`tests/unit/`](tests/unit/) at repo root, mirroring `infrastructure/lambda/catalog/` (one test module per source module). `pytest.ini` adds the Lambda src to `pythonpath` so tests import `services.common.errors`, `bootstrap`, `index`, etc. directly.
- [x] **Hermetic by design:** no boto3/httpx in `tests/unit/requirements.txt` — only `pytest` and `coverage`. `boto3`, `Attr`, `Key`, and `botocore.config.Config` are patched at the module level inside [`repo.py`](infrastructure/lambda/catalog/services/course_management/repo.py) and [`storage.py`](infrastructure/lambda/catalog/services/course_management/storage.py); `lambda_bootstrap` is patched on the [`index`](infrastructure/lambda/catalog/index.py) module to control whether the handler sees a configured service. `uuid4` is patched in storage tests for deterministic key strings.

### Coverage by file
- [x] **`services/common`** — `test_errors.py` (10), `test_http.py` (10), `test_validation.py` (20).
- [x] **`services/course_management`** — `test_contracts.py` (14), `test_service.py` (30), `test_repo.py` (30) including the **lesson-SK regression pin** (`max(order)+1`, not `len(existing)+1`), `test_storage.py` (11), `test_controller.py` (50) covering the route table, `_api_error_response` mapping (`BadRequest`/`NotFound`/`Conflict`/generic 500 → `internal_error`), and per-action dispatch.
- [x] **Top-level** — `test_config.py` (13), `test_bootstrap.py` (10) including warm-cache identity, `test_index.py` (6) including 503 `catalog_unconfigured` and OPTIONS preflight when `service is None`.
- [x] **Total: 204 tests, suite under 0.5s, 100% statement coverage** of `infrastructure/lambda/catalog/**` (informational; no enforced threshold).

### CI
- [x] **`lambda-unit-tests` job** in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (PR + push gate). Runs `coverage run -m pytest tests/unit -q --junitxml=...`, prints a coverage report, appends the totals line to `$GITHUB_STEP_SUMMARY`, and uploads JUnit results as an `actions/upload-artifact@v4` artifact (`if: always()`). Not added to `deploy-backend.yml` — `main` is gated transitively via the existing CI workflow.

---

## 2026-05-03 — Post-auth deploy: SPA secrets checklist + output scripts

### Completed

- [x] Operator checklist in [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md): map **`StreamMyCourse-Auth-<env>`** outputs → GitHub Environment secrets (including **`VITE_API_BASE_URL`** from **`ApiEndpoint`** on **`streammycourse-api`** / **`StreamMyCourse-Api-prod`**), redeploy by pushing **`main`** (**Deploy** workflow); manual web workflows documented as optional.
- [x] [`scripts/set-github-auth-secrets-from-stack.ps1`](scripts/set-github-auth-secrets-from-stack.ps1) reads CloudFormation outputs and runs **`gh secret set … --env dev|prod`** for Cognito + API URL (`-WhatIf` / `-SkipApiBaseUrl` supported).
- [x] Helper scripts [`scripts/print-auth-stack-outputs.ps1`](scripts/print-auth-stack-outputs.ps1) and [`scripts/print-auth-stack-outputs.sh`](scripts/print-auth-stack-outputs.sh) print outputs plus suggested secret names and `.env` lines.
- [x] [`design.md`](design.md) §10 backend bullet on SPA Cognito secrets; [`roadmap.md`](roadmap.md) MVP baseline auth line; [`frontend/.env`](frontend/.env) comments pointing at the script and `VITE_COGNITO_DOMAIN`.

---

## 2026-05-03 — Teacher hosting in eu-west-1

### Completed

- [x] **Teacher CloudFormation** (`StreamMyCourse-TeacherWeb-dev` / `prod`) recreated in **`eu-west-1`**; ACM cert parameters remain **`us-east-1`** ARNs. **S3 bucket** naming in [`teacher-web-stack.yaml`](infrastructure/templates/teacher-web-stack.yaml) now includes **`${AWS::Region}`** in the global bucket name so a move between regions does not hit prolonged S3 name reuse conflicts.
- [x] **GitHub OIDC** inline policy **`StreamMyCourseGitHubDeployWeb`**: `cloudformation:DescribeStacks` for teacher stacks in **`eu-west-1`**, teacher S3 ARNs for `streammycourse-teacher-{env}-eu-west-1-{account}`, `cloudfront:CreateInvalidation` on **`arn:aws:cloudfront::YOUR_AWS_ACCOUNT_ID:distribution/*`** (repo file [`iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json) applied to the role).
- [x] **Workflow / script:** [`.github/workflows/deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml) **`AWS_REGION: eu-west-1`**; [`deploy.ps1`](infrastructure/deploy.ps1) no longer overrides teacher stacks to **`us-east-1`** ( **`web-cert`** still does). **CI** parses additional templates including teacher / web-cert / billing ([`ci.yml`](.github/workflows/ci.yml)).
- [x] **Docs:** [`infrastructure/README.md`](infrastructure/README.md), [`design.md`](design.md) (teacher deploy example), [`plans/architecture/adr-0007-web-hosting.md`](plans/architecture/adr-0007-web-hosting.md).

---

## 2026-05-03 — Teacher/prod CORS, Cognito callbacks, API Gateway stage drift

### Completed

- [x] **Prod API CORS:** [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) and [`infrastructure/deploy-environment.ps1`](infrastructure/deploy-environment.ps1) prod `CorsAllowOrigin` / `CORS=` now include **`https://teach.streammycourse.click`** alongside the student app and localhost; [`infrastructure/README.md`](infrastructure/README.md) dev example includes **`https://teach.dev.streammycourse.click`**. (Commit `f95c6a1` on `main`.)
- [x] **Prod Cognito:** Teacher (and student) app clients updated for hosted **`https://teach.streammycourse.click/`** and **`https://app.streammycourse.click/`**; GitHub Environment **`prod`** variables `TEACHER_*` / `STUDENT_*` callback and logout URL lists; **`StreamMyCourse-Auth-prod`** CloudFormation redeployed so parameters match.
- [x] **Dev verification:** Confirmed dev catalog **`ALLOWED_ORIGINS`**, **`streammycourse-api`** `CorsAllowOrigin`, GitHub **`dev`** Cognito URL variables, and dev teacher pool client include **`https://teach.dev.streammycourse.click/`**.
- [x] **Symptom `Authentication required` / `unauthorized` with Cognito on:** Caused when the **API Gateway stage** served an **old deployment** (methods in the API definition had Cognito, but the live stage did not). Mitigations: **`aws apigateway create-deployment`** for the REST API + stage when fixing drift; template fix **`CatalogApiDeploymentV5.Properties.Description: !Sub 'catalog-${LambdaCodeS3Key}'`** in [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) so each catalog zip change forces a **new deployment** (commit `bbf0b58`).
- [x] **Lambda:** [`infrastructure/lambda/catalog/services/common/http.py`](infrastructure/lambda/catalog/services/common/http.py) **`apigw_cognito_claims`** parses **`authorizer.claims`** when it is a **JSON string**; unit test in [`tests/unit/services/common/test_http.py`](tests/unit/services/common/test_http.py).

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Completed |
| 🔄 | In Progress |
| ⏳ | Pending |
| 📝 | Notes/Context |
| ⚠️ | Issues/Blockers |

---

*Last updated: 2026-05-03 (teacher CORS + Cognito URLs + API Gateway deployment drift + claims parsing)*
