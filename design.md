# StreamMyCourse — MVP Design Document

> **Status:** The **MVP defined in this document is shipped** and running in dev/prod. Further product scope, Phase 2 work, and the **engineering quality bar** (clean, maintainable code—prefer supported APIs over brittle UI hacks) are tracked in **[roadmap.md](./roadmap.md)** and **[ImplementationHistory.md](./ImplementationHistory.md)**. **Last updated:** 2026-05-04 · **Stack:** React 19 + AWS (Serverless)

A free video course platform where instructors upload content and students stream it. No payments in MVP — all courses are free.

---

## 1. MVP Goals

- **Launch fast:** 4-5 weeks to first users
- **Zero-cost start:** AWS free tier + on-demand pricing
- **Core loop:** Browse → Watch → Instructors upload → Publish

---

## 2. MVP Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-1 | Course catalog (browse) | Required |
| FR-2 | Course detail page (lessons list) | Required |
| FR-3 | Video playback (MP4) | Required |
| FR-4 | Minimal backend API (courses/lessons/playback URL) | Required |
| FR-5 | Instructor flows: create/edit course, lessons, presigned upload, mark video ready, publish (**optional** Cognito auth; can run open for demos) | Required |
| FR-6 | Catalog persistence: **deployed dev/prod** use **RDS PostgreSQL** (`USE_RDS=true` with `DB_*` + Secrets Manager). **DynamoDB** (single-table + `TABLE_NAME`) exists in code for **local / rollback** only — **deprecated and unused** in managed dev and prod. Lambda returns **503** `catalog_unconfigured` when neither mode is wired | Required |

**Out of scope:** Payments, enrollments, progress tracking, transcoding, DRM.

**In scope:** Instructor upload via presigned S3 URLs; draft/publish workflow backed by **PostgreSQL** in deployed environments (see §6).

---

## 3. MVP Architecture

```
React (Vite + TS + Tailwind)
        │
        ├── REST API via API Gateway → Lambda (Python): courses, lessons,
        │   publish, presigned upload-url, playback URL
        │
        └── MP4 playback direct from S3 (CloudFront deferred to Phase 2)
```

**Current Implementation:**
- Lambda package under `infrastructure/lambda/catalog/` (handler `index.lambda_handler`; not inline in YAML)
- **Modular layout (single deploy unit):** `services/course_management/` (controller → service → repo/storage), `services/common/` (HTTP/CORS helpers, validation, errors), `services/auth/` (user profile `GET /users/me`); composition in `bootstrap.py`; entry in `index.py`
- **User profile rows (RDS):** `users` is upserted on every successful Cognito sign-in by a **PostAuthentication** Lambda shipped with [`auth-stack.yaml`](infrastructure/templates/auth-stack.yaml) when `EnableUserProfileSync` and RDS parameters are set (CI passes the RDS stack + S3 zip). The same row is also created/updated lazily via **`GET /users/me`**. **POST /courses/{id}/enroll** always calls `get_or_create_profile` first so missing `users` rows cannot break the `enrollments` FK.
- **RDS PostgreSQL** catalog in **deployed dev/prod** (`USE_RDS=true`); VPC-attached Lambda with `DB_HOST` / `DB_NAME` / `DB_PORT` / `DB_SECRET_ARN` from the api stack (see §10). **DynamoDB** single-table path (`TABLE_NAME`, `USE_RDS=false`) remains for **local tooling or rollback** — **not** used in managed dev/prod
- S3 bucket CORS configured for browser PUT uploads
- API Gateway REST API with OPTIONS on routes; **GatewayResponses** for DEFAULT_4XX/5XX add CORS headers on error paths; stack parameter `CorsAllowOrigin` feeds Lambda `ALLOWED_ORIGINS`
- No CloudFront yet (direct S3 URLs for MVP simplicity)

**MVP scope:** API-invoked Lambda only (no event sources). Cognito is **optional** (enabled only when the API stack receives a User Pool ARN). MediaConvert/CloudFront-video are Phase 2.

---

## 4. AWS Services (MVP)

| Service | Use | Cost Estimate |
|---------|-----|---------------|
| **CloudFront** | CDN for static + MP4 | **Deferred to Phase 2** |
| **S3** | Static + MP4 storage | Free tier friendly (direct access for MVP) |
| **API Gateway** | Minimal REST API | Free tier friendly |
| **Lambda** | Minimal API handler | Free tier friendly |
| **DynamoDB** | **Deprecated in deployed dev/prod** — not used for catalog traffic; legacy single-table model retained in code for **rollback / local** only | On-demand (unused in managed dev/prod) |
| **RDS PostgreSQL** | **Canonical catalog store** in **deployed dev/prod** (`USE_RDS=true`): courses, lessons, enrollments, user profiles ([`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml), migrations under [`infrastructure/database/migrations/`](infrastructure/database/migrations/)) | `db.t4g.micro` (eligible free tier when applicable) |
| **CloudWatch** | Logs/metrics | Free tier |
| **Total** | | **Target: $0 on free tier** |

**Structured Logging (JSON)**
- All Lambda functions output JSON one-object-per-line for CloudWatch Logs Insights
- Fields: `timestamp` (ISO 8601 UTC), `level`, `logger`, `message`, `lambda_request_id`, `api_request_id`, `action`, `http_method`, `duration_ms`, `status_code`
- `LOG_LEVEL` environment variable controls verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL); default INFO
- DEBUG level emits startup warning: "DEBUG logging enabled - verify no sensitive data in production"
- PII is logged as-is without redaction per current configuration (operator responsible for log access controls)

---

## 5. Video Pipeline (MVP)

```
Manual upload (local) → S3 (MP4) → Lambda mints signed CloudFront GET (or S3 presigned fallback)
                         ↓
              CloudFront (OAC → private bucket); Trusted Key Groups when signing enabled; invalidation Lambda per env
```

- **Format:** MP4 only
- **Transcoding:** None in MVP
- **No event triggers:** No S3 event → Lambda (prevents loop/chaining)
- **Upload:** Presigned S3 URLs via Lambda (`POST /upload-url` with `courseId` + `lessonId`); lessons created under a course; after client upload, `PUT .../video-ready` marks lesson video **ready** (MVP trust model)
- **CORS:** S3 bucket configured for cross-origin PUT from browser; presigned playback GETs need **`Range`** / **`If-Range`** in the video bucket’s **`AllowedHeaders`** (see [`video-stack.yaml`](infrastructure/templates/video-stack.yaml)) so browsers can preflight and use byte-range requests for MP4.

---

## 6. Data (MVP)

**RDS PostgreSQL (deployed dev/prod):** Managed **dev** and **prod** APIs use **only** the relational path (`USE_RDS=true`). Schema: [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) — tables `courses`, `lessons`, `enrollments`, `users` (see [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md)). **DynamoDB catalog tables are deprecated** in these environments and are **not** used for application reads/writes.

**DynamoDB (legacy — rollback / local only):** Single table `StreamMyCourse-Catalog-{environment}` when `USE_RDS=false` and `TABLE_NAME` is set:

- `PK = COURSE#<id>`, `SK = METADATA` — course title, description, optional `thumbnailKey` (S3 key under `{courseId}/thumbnail/{uuid}.{ext}`), `status` (DRAFT / PUBLISHED), timestamps (**note:** `status` is a DynamoDB reserved word; updates must use `ExpressionAttributeNames` in `UpdateExpression`)
- `PK = COURSE#<id>`, `SK = LESSON#<lessonId>` — lesson id, title, `order`, `videoKey`, `videoStatus` (pending / ready), duration. `lessonId` (UUID) is the row identity; `order` is a service-owned attribute (display position, compacted to `1..N` on delete). Note: `order` is a DynamoDB reserved word; updates must use `ExpressionAttributeNames` (e.g. `#order`).
- `PK = USER#<cognitoSub>`, `SK = ENROLLMENT#<courseId>` — self-service course access for lesson list + playback when the API enforces Cognito (`enrolledAt`, optional `source`).

**Misconfiguration:** when neither persistence mode is wired (`USE_RDS=false` and no `TABLE_NAME`, or RDS env incomplete so the catalog cannot start), catalog routes return **503** with `code: catalog_unconfigured` (OPTIONS still returns CORS preflight). The handler error text may still mention `TABLE_NAME`; operators should treat **RDS env** as required for deployed stacks. When `ALLOWED_ORIGINS` is unset or parses to an empty allowlist, the handler returns **503** with `code: cors_misconfigured` and **no** `Access-Control-Allow-*` headers (fail-secure); set `ALLOWED_ORIGINS=*` only for deliberate local/dev tooling. Local UI must call a deployed API or a stack with persistence and CORS env set.

---

## 7. API Design (MVP)

### Courses
```
GET    /courses                          // List (published only for catalog); items may include thumbnailUrl (presigned GET)
POST   /courses                          // Create empty course (DRAFT)
GET    /courses/mine                     // Instructor dashboard: courses owned by caller (DRAFT + PUBLISHED); teacher/admin + Cognito when enforced; oldest-first (`created_at` ascending)
GET    /courses/{id}/preview             // Published-only outline + lessonsPreview [{id,title,order}]; no Cognito on this path when preview resource is deployed
GET    /courses/{id}                     // Full details; may include thumbnailUrl and enrolled (bool); Cognito authorizer when User Pool ARN is set
PUT    /courses/{id}                     // Update metadata
PUT    /courses/{id}/publish             // Publish (requires ≥1 ready lesson)
PUT    /courses/{id}/thumbnail-ready     // Body { thumbnailKey }; persist cover image after S3 PUT (see upload-url)
DELETE /courses/{id}                     // Delete course + lessons
POST   /courses/{id}/enroll              // Idempotent self-service enrollment (PUBLISHED only); Cognito when enforced
```

### Lessons
```
GET    /courses/{id}/lessons             // List lessons (enrollment or course owner/admin when Cognito enforced; no videoKey in JSON)
POST   /courses/{id}/lessons            // Create lesson (+ presign flow via upload-url)
PUT    /courses/{id}/lessons/{lid}      // Update lesson title
DELETE /courses/{id}/lessons/{lid}      // Delete lesson
PUT    /courses/{id}/lessons/{lid}/video-ready   // Mark uploaded video ready (MVP)
```

### Playback
```
GET  /playback/{courseId}/{lessonId}   // Presigned MP4 URL; same access rule as GET lessons when Cognito enforced
```

### Upload (Instructor)
```
POST /upload-url                       // Presigned S3 PUT: lesson video (courseId + lessonId) or
                                       // course thumbnail (courseId + uploadKind: "thumbnail", optional filename/contentType)
```

### User profile (Auth)
```
GET  /users/me                         // Returns a per-user profile row (requires Cognito authorizer when enabled)
```

---

## 8. React Frontend (MVP)

### Tech Stack
- **React 19** + **Vite**
- **TypeScript** (strict)
- **TailwindCSS** + **AWS Amplify v6** (`aws-amplify`) and **@aws-amplify/ui-react** (UI primitives; Radix primitives ship with Amplify UI—not a separate shadcn CLI scaffold)
- Fetch API (simple data fetching)
- HTML5 video player (MP4)

### Component Structure
```
frontend/                            # Vite project root
├── index.html                       # Same shell as student.html; Vite dev serves `/` from here (SPA fallback)
├── student.html                     # Student SPA HTML input → dist/student/index.html (production build)
├── teacher.html                     # Teacher SPA HTML input → dist/teacher/index.html
├── vite.student.config.ts           # Student dev + build (proxy, student.html input)
├── vite.teacher.config.ts           # Teacher dev + build
└── src/
    ├── student-main.tsx             # Student site entry point
    ├── teacher-main.tsx             # Teacher site entry point
    ├── student-app/
    │   ├── App.tsx                  # Student-only routes (view-only)
    │   └── StudentHeader.tsx        # Student navigation (no instructor links)
    ├── teacher-app/
    │   ├── App.tsx                  # Teacher-only routes (dashboard, management)
    │   └── TeacherHeader.tsx        # Teacher navigation (dashboard link, view student site)
    ├── style.css
    ├── components/
    │   ├── layout/                  # Footer, Layout (gradient + main + footer; optional `chromeHeader` for fixed app nav)
    │   └── course/                  # CourseCard, CourseGrid, skeletons, thumbnail editor
    ├── lib/
    │   └── api.ts                   # API client (fetch + env base URL)
    └── pages/
        ├── CourseCatalogPage.tsx
        ├── CourseDetailPage.tsx
        ├── LessonPlayerPage.tsx
        ├── InstructorDashboard.tsx  # Teacher dashboard
        └── CourseManagement.tsx     # Course editing and upload
```

### Subdomain-Based Site Separation
The frontend is built as **two separate SPAs** deployed to different subdomains:

| Site | Domain | Purpose | Routes |
|------|--------|---------|--------|
| **Student** | `streammycourse.com` | Browse and watch courses | `/`, `/login`, `/courses/:id`, `/courses/:id/lessons/:id` |
| **Teacher** | `teach.streammycourse.com` | Create, edit, upload content | `/`, `/courses/:id` |

### Student Site Routes (View-Only)
```
/                                    # Course catalog
/login                               # Student sign-in (Hosted UI / auth shell)
/courses/:courseId                   # Course detail
/courses/:courseId/lessons/:lessonId # Video player
```

### Teacher Site Routes
```
/                                    # Instructor dashboard (create/list courses)
/courses/:courseId                   # Course management (edit, lessons, upload, publish)
```

### Build Configuration
- `vite.student.config.ts` → Build: `npm run build:student` → Output: `dist/student/`
- `vite.teacher.config.ts` → Build: `npm run build:teacher` → Output: `dist/teacher/`
- `npm run build:all` → Builds both sites

**Local dev:** set `VITE_API_BASE_URL` (see `frontend/.env.example` — copy to `frontend/.env`). Typical pattern: `VITE_API_BASE_URL=/api` with Vite proxy **`VITE_API_PROXY_TARGET`** set to your API Gateway root (required for `npm run dev` / `dev:student` / `dev:teacher` when using `/api`; default **`npm run dev`** uses [`vite.student.config.ts`](frontend/vite.student.config.ts)). Production relies on API CORS configuration. Vite `server.host: true` exposes a **Network** URL so phones on the same LAN use `http://<PC-LAN-IP>:<port>` (not `127.0.0.1` on the phone).

---

## 9. Security (MVP)

### API Safety (No Looping)
- Lambda is invoked **only** by API Gateway (no S3 events, no SNS/SQS, no scheduled triggers).
- This prevents infinite chains/loops in the MVP.

### Basic Protections
- S3 bucket: Private with presigned URL access (PUT for upload, GET for playback)
- Lambda IAM: `s3:PutObject` and `s3:GetObject` on `${bucket}/*` (upload + presigned playback; object keys are course/lesson-scoped under the same bucket); **RDS** path uses VPC + Secrets Manager + relational access; legacy DynamoDB policy applies only if the stack still attaches catalog table permissions for rollback
- CORS: Origin validation with configurable allowlist (`ALLOWED_ORIGINS`, set from CloudFormation `CorsAllowOrigin`); no implicit wildcard (empty env means misconfiguration). Use `ALLOWED_ORIGINS=*` only when intentionally allowing any origin in dev/tools. API Gateway GatewayResponses add CORS headers on 4XX/5XX
- Presigned uploads: allowed **video / image** `Content-Type` only; S3 keys are `{courseId}/lessons/{lessonId}/video/{uuid}.{ext}` for lesson video, `{courseId}/lessons/{lessonId}/thumbnail/{uuid}.{ext}` for lesson thumbnails, and `{courseId}/thumbnail/{uuid}.{ext}` for course cover; presigned playback **GET** only for keys matching those layouts (validated in Lambda); conditional **repo** update when persisting a new **`videoKey`** after presign (mitigates concurrent upload races). **Note:** `boto3` presigned PUT URLs do not attach policy **Conditions** (e.g. `content-length-range`); document size limits for clients; S3 caps a single PUT at **5 GiB**.
- API stage **throttling** on the catalog stage; **`GatewayResponseAllowOrigin`** is parameterized (default tightened away from `*` for dev/local)
- Video stack S3: **Block Public Access**, **SSE-S3** encryption, CORS allowlist parameter (no wildcard origin); **`Range`** / **`If-Range`** allowed for cross-origin HTML5 `<video>` playback
- **Legacy** DynamoDB catalog table in **prod** (if retained): **Retain** + **PITR** enabled — **not** the live store when `USE_RDS=true`. RDS backups/PITR follow operator settings on the instance.
- Lambda JSON responses: **`X-Content-Type-Options`**, **`X-Frame-Options`**, **`Content-Security-Policy`** (API-oriented restrictive policy), **`Cache-Control: no-store`** on errors; **HSTS** when the response includes an **HTTPS** `Access-Control-Allow-Origin`
- Edge-hosted SPAs ([`edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml)): CloudFront **response headers policy** (HSTS, nosniff, frame deny, referrer policy) on default behaviors
- **Optional auth:** When `CognitoUserPoolArn` is set on the API stack, API Gateway uses a **Cognito user pools authorizer** on protected routes and Lambda enforces role/ownership checks (`COGNITO_AUTH_ENABLED=true`). Hosted student/teacher SPAs backed by **`StreamMyCourse-Auth-*`** use **Google-only** pool clients (no native username/password on those clients), shrinking phishing/brute-force surface on public sign-in compared to parallel native + social.
- **API Gateway vs Lambda:** The stage must point at a **deployment** that includes those authorizer settings. If the stage lags the REST API definition (CloudFormation updated methods but not the deployment snapshot), the browser can send a valid `Authorization` bearer while Lambda still sees **no** `requestContext.authorizer.claims` and returns **`Authentication required`** (`code: unauthorized`). The API stack ties **`AWS::ApiGateway::Deployment`** `Description` to **`LambdaCodeS3Key`** so each catalog zip upload publishes a new deployment; if drift is suspected, operators can run **`aws apigateway create-deployment`** for the REST API id and stage (see [`ImplementationHistory.md`](./ImplementationHistory.md)).
- No DRM and no recording prevention in MVP.
- No sensitive data in logs (console logs removed from frontend)

---

## 10. Deployment (MVP)

### Frontend (Static Hosting)

Two separate SPAs are hosted on AWS using S3 + CloudFront + Route 53:
- **Student site:** `streammycourse.com` — browse and watch courses
- **Teacher site:** `teach.streammycourse.com` — create and manage courses

**Architecture:** Private S3 bucket (Origin Access Control) → CloudFront CDN → Route 53 alias (per site)

**One-time setup (per environment):**
```powershell
# 1. Register domain via Route 53 console (manual, captures DomainName and HostedZoneId)

# 2. Deploy unified edge-hosting stack (ACM + student + teacher hosting) in us-east-1
#    CloudFront ACM requirement: certificate must be in us-east-1.
cd infrastructure
.\deploy.ps1 -Template edge-hosting -StackName StreamMyCourse-EdgeHosting-dev `
    -Environment dev `
    -HostedZoneId Z123456789 `
    -DomainName dev.streammycourse.click `
    -TeacherDomainName teach.dev.streammycourse.click `
    -CertPrimaryDomain dev.streammycourse.click `
    -AttachCloudFrontAliases true
```

**CI/CD deployment (every push to `main`):**
- **Unified Deploy:** [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — after CI: **backend integ** and **integ tests**, then **`deploy-edge-dev`** ([`scripts/deploy-edge.sh`](scripts/deploy-edge.sh)) for **`StreamMyCourse-EdgeHosting-dev`** in **`us-east-1`** (ACM + both SPAs’ S3 + CloudFront + Route 53 in one stack). Then **dev backend** (auth + [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh)), **student web**, and **teacher web** run **in parallel**. **`deploy-edge-prod`** runs **in parallel with those three** once integ tests and **dev edge** succeed (it does **not** wait for dev Lambda or SPA deploys). **Prod** backend and both prod SPAs run only after **prod edge** **and** after **integ**, **integ tests**, **dev edge**, **dev backend**, and **both dev SPAs** have succeeded. Reusable SPA workflows read bucket and distribution IDs from the edge stack outputs. GitHub Environment variables **`ROUTE53_HOSTED_ZONE_ID`**, **`STUDENT_WEB_DOMAIN`**, **`TEACHER_WEB_DOMAIN`**, optional **`WEB_CERT_DOMAIN`** / **`WEB_CERT_SANS`**, and **`COGNITO_DOMAIN_PREFIX`** (required for full deploy) are documented in [`infrastructure/README.md`](infrastructure/README.md).
- **Lambda zip:** `catalog-{env}-{gitSha12}.zip` so CloudFormation updates the function each commit.
- **OIDC:** `AWS_DEPLOY_ROLE_ARN`; bootstrap the role with [`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) via [`scripts/deploy-github-iam-stack.sh`](scripts/deploy-github-iam-stack.sh) / [`.ps1`](scripts/deploy-github-iam-stack.ps1) (**not** in CI/CD). The template creates an **`AWS::IAM::OIDCProvider`** when the account has no GitHub issuer yet; if `https://token.actions.githubusercontent.com` already exists, pass **`ExistingGithubOidcProviderArn`** (IAM allows one provider per that URL per account—deleting the CloudFormation stack does not remove a pre-existing provider). Policy statements mirror [`infrastructure/iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json) + [`iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) (backend policy includes **ACM us-east-1**, **Route 53**, **CloudFront** for edge stacks; **CloudFormation / Lambda / DynamoDB (if used) / RDS / logs** scoped to **`StreamMyCourse-*`** where feasible—S3 stays account-scoped for artifacts and generated video bucket names). SPA reusable workflows ([`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml), [`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml)) declare **`workflow_call` secrets**; [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) passes them explicitly (no blanket **`secrets: inherit`** on those calls). After changing IAM JSON or the template, sync the live role: [`scripts/apply-github-deploy-role-policies`](scripts/apply-github-deploy-role-policies.sh) or redeploy the IAM stack. Details: [`infrastructure/README.md`](infrastructure/README.md).
- **Concurrency:** `cancel-in-progress: false` on deploy workflows so overlapping pushes **queue** (no mid-deploy cancellation)

**SPA HTML entrypoints (important):**
- **Student** build uses `frontend/student.html` → `frontend/src/student-main.tsx`; build renames output to **`dist/student/index.html`** for CloudFront `DefaultRootObject`.
- **Teacher** build uses `frontend/teacher.html` → `frontend/src/teacher-main.tsx`; build renames output to **`dist/teacher/index.html`** (same pattern as student).

**Cache strategy:**
- `assets/*` (hashed files): `max-age=31536000,immutable` (1 year)
- `index.html`: `no-cache` (always fresh)
- Other root files: `max-age=3600` (1 hour)

**CORS configuration:** When adding hosted origins, update the API stack to include both student and teacher domains:
```powershell
.\deploy.ps1 -Template api -StackName ... `
    -CorsAllowOrigin "https://app.streammycourse.com,https://teach.streammycourse.com,http://localhost:5173,http://localhost:5174" `
    -GatewayResponseAllowOrigin "http://localhost:5173"  # or a specific origin for error responses
```

### Backend
- Deploy API Gateway + Lambda via CloudFormation ([`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml)); **deployed dev/prod** attach **RDS** (`RdsStackName` + `UseRds=true`). A DynamoDB **CatalogTable** may still exist in the template for legacy stacks; **managed dev/prod traffic uses PostgreSQL only** — DynamoDB is deprecated there.
- Lambda code packaged as a zip and uploaded to an artifacts S3 bucket; stack references `LambdaCodeS3Bucket` / `LambdaCodeS3Key`. **CI and [`deploy.ps1`](infrastructure/deploy.ps1)** use a **git-SHA-based key** (`catalog-{env}-{sha}.zip`) so each deploy changes the parameter and the stack updates Lambda (fixed keys caused empty changesets). The same key is referenced from **`CatalogApiDeploymentV8.Description`** in [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) so **API Gateway** also receives a **new deployment** when the artifact changes (avoids a stage serving an older snapshot while methods in the console already show Cognito). The deployment resource logical id is occasionally bumped so template-only route changes still replace the stage snapshot.
- **Auth stack (Cognito):** On each **dev** / **prod** full deploy, [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) **requires** GitHub Environment variable **`COGNITO_DOMAIN_PREFIX`** and GitHub Environment secrets **`GOOGLE_OAUTH_CLIENT_ID`** + **`GOOGLE_OAUTH_CLIENT_SECRET`** (dedicated fail-fast steps), then packages [`infrastructure/lambda/cognito_user_profile_sync/`](infrastructure/lambda/cognito_user_profile_sync/) to S3 and runs `aws cloudformation deploy` for `StreamMyCourse-Auth-<env>` with **Google OAuth parameters always**, **`RdsStackName`**, **`EnableUserProfileSync=true`**, and the sync Lambda S3 keys when RDS is in use. It passes **`UserPoolArn`** into `scripts/deploy-backend.sh` via `COGNITO_USER_POOL_ARN` so the API stack gets `CognitoUserPoolArn`. Local auth deploy: `.\infrastructure\deploy.ps1 -Template auth` **must** include **`-GoogleClientId`** and **`-GoogleClientSecret`** (script validates non-empty); optional **`-RdsStackName`**, **`-EnableUserProfileSync`**, and sync code bucket/key when wiring the PostAuthentication Lambda locally.
- **SPA Cognito env (after auth stack exists):** Builds read **`VITE_COGNITO_*`**, **`VITE_API_BASE_URL`**, and **`VITE_COGNITO_DOMAIN`** from GitHub **Environment** secrets (`dev` / `prod`) via [`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml) and [`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml). Use [`scripts/set-github-auth-secrets-from-stack.ps1`](scripts/set-github-auth-secrets-from-stack.ps1) (AWS + `gh`) or [`scripts/print-auth-stack-outputs.ps1`](scripts/print-auth-stack-outputs.ps1) / [`.sh`](scripts/print-auth-stack-outputs.sh) plus [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md); then push **`main`** so the **Deploy** workflow rebuilds SPAs (manual web workflows are optional). **`npm run build:student` / `build:teacher`** run [`scripts/check-cognito-spa-env.mjs`](scripts/check-cognito-spa-env.mjs) first: if pool id and client id are set, **`VITE_COGNITO_DOMAIN`** must be set or the build fails (unit-tested in [`tests/unit/test_cognito_spa_env_contract.py`](tests/unit/test_cognito_spa_env_contract.py)). **Runtime parity:** Amplify configures **Hosted UI OAuth only** ([`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts)); SPA code treats Cognito/auth as configured only when **pool id**, **client id**, and **`VITE_COGNITO_DOMAIN`** are all present (Vitest predicate in [`frontend/src/lib/cognito-hosted-ui-env.test.ts`](frontend/src/lib/cognito-hosted-ui-env.test.ts)).
- **Google-only public clients:** The auth stack template ([`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml)) always provisions **Google** as the identity provider and sets student/teacher app clients to **`SupportedIdentityProviders: [Google]`** only; **`GoogleClientId` / `GoogleClientSecret`** are **required** parameters. Native password/SRP **ExplicitAuthFlows** are not enabled on those clients (OAuth code + refresh). SPAs use Google sign-in via **[`frontend/src/components/auth/SignIn.tsx`](frontend/src/components/auth/SignIn.tsx)** (custom Hosted UI redirect with **`signInWithRedirect`**; **`AuthenticatorProvider`** + **`useAuthenticator`** for session state—no Amplify `<Authenticator>` form) and [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md).
- **Post-login SPA navigation:** Hosted UI returns to **`/`**; the app stores the pre-login in-SPA path in **`sessionStorage`** (sanitized in [`frontend/src/lib/post-login-return.ts`](frontend/src/lib/post-login-return.ts)) before **`signInWithRedirect`**, and [`frontend/src/components/auth/PostLoginRedirect.tsx`](frontend/src/components/auth/PostLoginRedirect.tsx) restores it after **`authStatus`** becomes **`authenticated`**. Each SPA entry ([`frontend/src/student-main.tsx`](frontend/src/student-main.tsx), [`frontend/src/teacher-main.tsx`](frontend/src/teacher-main.tsx)) mounts **`AuthenticatorProvider`** around **`BrowserRouter`** so auth hooks work on shell chrome ([`frontend/src/components/layout/Layout.tsx`](frontend/src/components/layout/Layout.tsx) **`chromeHeader`** → [`StudentHeader`](frontend/src/student-app/StudentHeader.tsx) / [`TeacherHeader`](frontend/src/teacher-app/TeacherHeader.tsx)) and **`/login`** ([`frontend/src/pages/StudentLoginPage.tsx`](frontend/src/pages/StudentLoginPage.tsx)).
- No event sources in MVP (no S3 triggers, no schedules)
- **RDS PostgreSQL (deployed dev/prod):** [`infrastructure/templates/rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) provisions a 1-AZ VPC, private **`db.t4g.micro`** (PostgreSQL 16, encrypted), Secrets Manager credential (auto-generated), and Interface / Gateway VPC endpoints. Pass **`RdsStackName`** and set **`UseRds=true`** on the api stack: [`api-stack.yaml`](infrastructure/templates/api-stack.yaml) imports SubnetIds / SecurityGroupIds to attach the Lambda to the VPC, injects `DB_HOST/PORT/NAME/SECRET_ARN`, and raises the Lambda timeout to **30s** (VPC cold start + Secrets Manager fetch). [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) / [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1) vendor **`psycopg2-binary`** for `manylinux2014_x86_64` into the Lambda zip (see [`requirements.txt`](infrastructure/lambda/catalog/requirements.txt) + [`_vendor_bootstrap.py`](infrastructure/lambda/catalog/_vendor_bootstrap.py)). Runbook: [`tests/integration/README.md`](tests/integration/README.md); rationale: [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md). **DynamoDB is deprecated** for managed dev/prod (unused); emergency rollback to DynamoDB would set `UseRds=false` and supply `TABLE_NAME` **only if** a table is still provisioned and migrated data is acceptable.
- **RDS dev rollout via CI/CD:** [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) chains **`deploy-rds-dev`** (upload a small **schema-applier** Lambda zip to the artifacts bucket, then deploy `StreamMyCourse-Rds-dev` with `SchemaApplierCodeS3Bucket` / `SchemaApplierCodeS3Key` so [`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) provisions **`StreamMyCourse-RdsSchemaApplier-<env>`** in the private subnet) → **`apply-schema-dev`** (`aws lambda invoke` on that function; DDL runs inside the VPC, no `psql` from the runner) → **`deploy-backend-dev`** (`RDS_STACK_NAME` + `USE_RDS=true`) → **`verify-dev-rds`** ([`tests/integration/test_rds_path.py`](tests/integration/test_rds_path.py)). Source: [`infrastructure/lambda/rds_schema_apply/index.py`](infrastructure/lambda/rds_schema_apply/index.py). Prod mirrors the chain: **`deploy-rds-prod`** → **`apply-schema-prod`** → **`deploy-backend-prod`** → **`verify-prod-rds`** (see [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)).
- **Verify dev / prod RDS auth:** **`verify-dev-rds`** and **`verify-prod-rds`** call [`.github/workflows/verify-rds-reusable.yml`](.github/workflows/verify-rds-reusable.yml) with **`github_environment: dev`** or **`prod`** plus stack inputs only. Each GitHub Environment stores the **same secret/variable key names** (**`COGNITO_RDS_VERIFY_TEST_PASSWORD`**, optional **`COGNITO_RDS_VERIFY_JWT`**, optional **`COGNITO_RDS_VERIFY_TEST_USERNAME`**); values are per-environment. The reusable job mints a Cognito **IdToken** via **`AdminInitiateAuth`** against the **auth stack passed as input** (dev vs prod). Runtime pytest env **`INTEG_COGNITO_JWT`** is set by the job (not a GitHub secret name). Bootstrap user: [`scripts/ensure-ci-rds-verify-cognito-user.sh`](scripts/ensure-ci-rds-verify-cognito-user.sh); details: [`tests/integration/README.md`](tests/integration/README.md).
- Run: `cd infrastructure && .\deploy.ps1 -Template api -StackName <stack> -VideoBucketName <bucket>` (ensure `aws` is on PATH; full path `C:\Program Files\Amazon\AWSCLIV2\aws.exe` on Windows if needed)

### CI
- GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): frontend `npm ci`, **ESLint** (`npm run lint`), **Knip** (`npm run knip`), **`npm run build:all`** (student + teacher production builds, including Cognito env contract), **`npm run test`** (Vitest SPA unit tests, including **jsdom** auth UI tests under `frontend/src/**/*.dom.test.tsx` such as [`SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx)); Lambda Python compile; **Vulture** (dead code); **Radon** `cc` (complexity, informational / `continue-on-error`); YAML parse for CloudFormation templates (including [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) for CI sanity on the IAM bootstrap template); **actionlint** on `.github/workflows`; **boundary import check** ([`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py)); Lambda **unit tests** including a **`bash -n`** guard on [`scripts/deploy-edge.sh`](scripts/deploy-edge.sh) and [`tests/unit/test_cognito_spa_env_contract.py`](tests/unit/test_cognito_spa_env_contract.py) for [`scripts/check-cognito-spa-env.mjs`](scripts/check-cognito-spa-env.mjs)

### Architecture notes (repo)
- Module map and ADRs: [`plans/architecture/`](plans/architecture/)
- Cursor rule for layers: [`.cursor/rules/clean-architecture-boundaries.mdc`](.cursor/rules/clean-architecture-boundaries.mdc)

### Environments
- **Dev:** Local development (default `http://localhost:5173`; another port if 5173 is busy — use the URL Vite prints)
- **CI / deployed backends and SPAs:** GitHub Actions on **`main`** use **`dev`** and **`prod`** GitHub [Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment) (see [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)); there is **no** separate automated staging stack or per-feature branch deploy workflow in this repository today (branch previews could be added later without changing the MVP contract).
- **Prod:** Production deploys from **`main`** after CI and the deploy pipeline succeed

---

## 11. MVP Success Metrics

| Metric | Target |
|--------|--------|
| Time to usable demo | 1-2 days |
| Monthly AWS cost | $0 on free tier |
| Video load time | < 3 seconds |
| Concurrent users | 20 (initial) |

---

## 12. MVP Design Decisions (Locked)

| Question | Decision | Notes |
|----------|----------|-------|
| **Auth Provider** | Cognito (optional on API); hosted student/teacher SPAs use **Google federation only** (`StreamMyCourse-Auth-*` template) | Native password sign-in not enabled on public SPA app clients; break-glass via Google + Console `custom:role` ([`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md)) |
| **Lambda Runtime** | Python | Better for media processing libraries |
| **Admin Tasks** | **RDS / SQL** (or legacy DynamoDB console only if on rollback path) | Direct data access for moderation; admin UI in Phase 3 |
| **Categories** | Flexible | Teacher/student role split is the key distinction; categories can be added dynamically |
| **Upload Limits** | 10GB per file | No time limit on video duration |
| **Local Testing** | Yes | Local dev with AWS dev credentials; LocalStack optional for offline testing |
| **Forgot Password** | N/A (MVP) | Deferred |
| **Course Status** | Draft → Published | 2-state workflow (no pending review) |
| **DRM Provider** | None (MVP) | Deferred |

### User Roles
- **Hosted SPAs:** With Cognito configured for Google federation (auth stack + SPA env), student and teacher sites require **Google sign-in** for protected flows; operator promotion uses Console **`custom:role`**. Preview/catalog read policies remain as implemented in the API stack (some routes stay public by design).

---

## 13. Near-term backlog (after current MVP)

Ordered engineering priorities before large Phase 2 (monetization / DRM) work. Details and history: [`ImplementationHistory.md`](./ImplementationHistory.md); architecture decisions: [`plans/architecture/`](./plans/architecture/).

| Priority | Item | Goal |
|----------|------|------|
| 1 | **CloudFront (video)** | **Shipped:** CDN for MP4 via [`video-stack.yaml`](infrastructure/templates/video-stack.yaml); **Signed URLs** when SSM public PEM + Secrets Manager private key + api-stack params are wired (see [`scripts/deploy-cloudfront-keys-stack.sh`](scripts/deploy-cloudfront-keys-stack.sh)); **`https-only`** viewer policy; optional **`TrustedKeyGroups`**; OAC + bucket policy; **S3 presigned GET** remains rollback when signing env is unset; catalog invokes **`StreamMyCourse-CfInvalidate-<env>`** after media-affecting mutations; default **`MEDIA_GET_EXPIRES_SECONDS=28800`** (8h). |
| 2 | **Frontend hosting** | **Shipped:** dual SPAs (student + teacher) to S3 + CloudFront + Route 53 via [`edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml) and the deploy pipeline (see §10). **Remaining:** ops polish (monitoring, cache tuning, domain/certificate hygiene). |
| 3 | **Auth** | **Shipped:** Cognito pool + required Google IdP + Google-only student/teacher app clients; API authorizer + `GET /users/me` + SPA Amplify Hosted UI OAuth + **`SignIn`** shell. **Ops:** GitHub **`TEACHER_*` / `STUDENT_*` callback URLs**, **`GOOGLE_OAUTH_*`** secrets per env (required for full deploy), and API **`CorsAllowOrigin`** must match hosted origins. **Remaining:** tighten which routes are public vs Cognito-only (catalog still has open reads by design). |
| 4 | **RDS PostgreSQL (catalog)** | **Shipped and live in deployed dev/prod:** [`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml), API **`UseRds=true`**, PostgreSQL adapters (`services/*/rds_repo.py`), migrator [`scripts/migrate-dynamodb-to-rds.py`](scripts/migrate-dynamodb-to-rds.py). **DynamoDB catalog is deprecated** in managed dev/prod (unused). **Remaining:** optional cleanup of idle DynamoDB tables/IAM, tighter docs for pure-local DynamoDB dev. See [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md) and [`tests/integration/README.md`](tests/integration/README.md). |

**Technical hygiene (ongoing):** extend typed `contracts` at the controller edge as endpoints grow. (Lambda artifact keys: **shipped** in CI/`deploy.ps1` — see §10.)

---

## 14. Post-MVP roadmap (Phase 2+)

See [`roadmap.md`](./roadmap.md) for phased vision (monetization, DRM/Kinescope option, scale, admin, search, live streaming) and cost notes. §13 is the **bridge** between today’s MVP and that document’s Phase 2.

---

*End of MVP Design Document*
