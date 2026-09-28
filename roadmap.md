# StreamMyCourse — Full Architecture Roadmap

> **Status:** **Post-MVP evolution** (MVP baseline shipped; Phase 2+ ahead) · **Last updated:** 2026-09-28

This document is the **long-range** product and architecture vision (Phase 2 onward). The current **MVP contract** (what is built, APIs, data model, deployment) lives in [design.md](./design.md). **Near-term engineering priorities** (CloudFront, SPA hosting, auth) are listed there as §13 and mirrored below so this file stays navigable without opening multiple docs.

**Engineering bar (post-MVP):** Ship **clean, intentional implementations**—prefer **documented component APIs** over brittle UI hacks. **Student auth (RS-6):** Google Hosted UI redirect **plus** custom email/password pages (Amplify **`signUp` / `signIn`**, SRP)—**no** Amplify `<Authenticator>` widget. **Teacher auth:** Google-only **[`SignIn.tsx`](frontend/src/components/auth/SignIn.tsx)** + **`signInWithRedirect`**. Regression coverage in student login/register DOM tests and **[`SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx)**.

---

## MVP baseline (shipped)

Roughly what exists today before Phase 2 work:

- **Frontend:** React 19 (Vite + TS + Tailwind), student **Home** (`/`, Research Spectrum marketing; course cards from public `GET /courses` with **USD prices** when set), public **About** (`/about`), **FAQ** (`/faq`), **Contact** form (`/contact` → public **`POST /contact`**, Zoho SMTP via SQS worker — RS-10), **Research Team** explainer (`/research-team`, no application), **Details** at **`/details`** (legacy), **Courses** catalog at **`/courses`** (legacy **`/catalog`** redirect), signed-in **dashboard** at **`/dashboard`** (legacy **`/my-course`** redirect), course detail (**USD prices** + **purchase** CTAs when `hasAccess === false`), lesson player (including **module quiz** entry in the sidebar and **Next** to `/courses/:courseId/modules/:moduleId/quiz` after the last lesson in a module when `moduleQuiz` is available; **RS-8** pass mark, **locked** modules when prior quiz not passed, attempt history on quiz page; **RS-11** **Resources** / **Downloads** tabs for instructor-uploaded lesson files and **Notes** tab for private per-student notes), plus instructor dashboard and course management (instructor **pass %** per module quiz; **RS-11** attach/list/delete lesson files on each lesson row). **Billing (pre-go-live, RS-5):** mock **`POST /billing/checkout-session`** `{ productType, courseId? }` + **`/billing/success`** / **`/billing/cancel`** return routes; **`GET /billing/bundle`**, **`GET /billing/purchases`**; student **`/checkout`**, **`/account/purchases`** — see [`design.md` §13](./design.md) and [`plans/ui-overhaul/rs-5-one-time-purchases.md`](plans/ui-overhaul/rs-5-one-time-purchases.md). **Hosted** as **two SPAs** (student + teacher) on S3 + CloudFront + Route 53 via **`StreamMyCourse-EdgeHosting-prod`** in **`us-east-1`** (unified stack). On **`main`**, **[`deploy-backend.yml`](.github/workflows/deploy-backend.yml)** drives prod SPA asset deploys after edge + backend + integration tests (with **[`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml)** / teacher reusable). Student UI gaps vs Figma/backend are listed in **[`reports/figma-student-ui-gap-report.md`](reports/figma-student-ui-gap-report.md)**.
- **API:** API Gateway REST → single Python Lambda (`infrastructure/lambda/catalog/`), layered **controller → service → repo** with `plans/architecture/` ADRs and CI boundary checks. **CI** then **Deploy** ([`deploy-backend.yml`](.github/workflows/deploy-backend.yml) after green [`ci.yml`](.github/workflows/ci.yml)) runs video + API + edge + SPAs via [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) / reusable web workflows: **prod** edge, RDS, backend, integration HTTP tests, verify prod RDS, then both prod SPAs (see workflow graph for exact ordering).
- **Data:** **RDS PostgreSQL** is the **only** persistence path — [`infrastructure/templates/rds-stack.yaml`](infrastructure/templates/rds-stack.yaml), Lambda VPC + `DB_*` wiring in [`api-stack.yaml`](infrastructure/templates/api-stack.yaml), `services/<context>/rds_repo.py`, migrations under [`infrastructure/database/migrations/`](infrastructure/database/migrations/). DynamoDB path was fully removed; `RdsStackName` is now a required parameter for api stack deploy. S3 presigned **SigV4** upload/playback (regional endpoint); MP4 playback **primarily** via presigned S3 GET; **video** stack also provisions **CloudFront + OAC** on the private bucket for a correct CDN path and cache invalidation (see `design.md` §5 / §13). **Question banks:** migrations **006**–**010** (bank name schema folded into [`006_question_banks_module_quizzes.sql`](infrastructure/database/migrations/006_question_banks_module_quizzes.sql)); create/list/rename bank names, module quiz, draft MCQ, publish with `n` + `moduleId`; MCQ validation ([`mcq_validation.py`](infrastructure/lambda/catalog/services/question_banks/mcq_validation.py)); **QB-D** optional `moduleQuiz` on modules list + passive badge; **QB-F** per-student bindings ([`binding_draw.py`](infrastructure/lambda/catalog/services/question_banks/binding_draw.py)); **QB-G** `module_quiz_attempts` + presentation shuffle; **QB-H/I** `POST .../quiz/submit`, equal-weight grading ([`grading.py`](infrastructure/lambda/catalog/services/question_banks/grading.py)), `POST .../quiz/start` phases (`in_progress` / `latest_results`, optional `retake`, `latestSubmission`), persisted submissions in **`module_quiz_attempt_submissions`**. Student quiz routes remain bank-name-free: [`ModuleQuizPage.tsx`](frontend/src/pages/ModuleQuizPage.tsx) + [`api.ts`](frontend/src/lib/api.ts) via [`StudentModuleQuizAuth.tsx`](frontend/src/components/auth/StudentModuleQuizAuth.tsx). **RS-8:** migration **018** `pass_percent`, **`PATCH …/quiz`**, **`GET …/quiz/attempts`**, module chain gating ([`gating.py`](infrastructure/lambda/catalog/services/question_banks/gating.py)) — [`plans/ui-overhaul/rs-8-quiz-gating.md`](plans/ui-overhaul/rs-8-quiz-gating.md); **prod 018 pending** pre-launch. Unit suite under [`tests/unit/services/question_banks/`](tests/unit/services/question_banks/) (incl. grading, submit, gating, attempts); HTTPS integration authored in [`test_question_bank_start.py`](tests/integration/test_question_bank_start.py) and [`test_question_bank_submit.py`](tests/integration/test_question_bank_submit.py), plus permissions/publish/visibility/publisher reads (**CatalogApiDeploymentV27**+ route in template; schema **008–010** when pipeline apply-schema runs).
- **Video provider cutover:** catalog now uses a provider port (`services/course_management/video_providers/port.py`) with `VIDEO_PROVIDER` selection in `bootstrap.py`; `kinescope` is the default. Playback API can return provider contract `{ provider, videoId, drmAuthToken }`; provider callbacks are `POST /webhooks/kinescope` and `POST /webhooks/kinescope/drm-auth`; Kinescope cleanup IDs flow through async media-cleanup payloads.
- **Auth (optional on API):** Cognito user pool via CloudFormation (`StreamMyCourse-Auth-prod`); API authorizer when the pool ARN is passed on backend deploy. **Student single-session** (one active student session per user; teacher client exempt; **`session_superseded`** API guard + Cognito Pre Token refresh deny) — implemented in repo; see [`design.md` §9](./design.md) and [`plans/student-single-session-refresh-spike.md`](plans/student-single-session-refresh-spike.md). Public reads remain public, but are wired to a **permissive API Gateway REQUEST authorizer** so authenticated callers can supply `sub`/`role` context without any Cognito/JWKS calls from the in-VPC catalog Lambda. **Auth template** ([`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml)): **`GoogleClientId` / `GoogleClientSecret`** required; **student** client **`SupportedIdentityProviders: [COGNITO, Google]`** with **SRP** + OAuth; **teacher** client **Google-only**; **PreSignUp** linking + **Zoho CustomEmailSender** (`ZOHO_SMTP_PASSWORD` / `streammycourse/zoho-smtp/prod`). Catalog **`PATCH /users/me`** + migration **016**; student **terms gate**. Stack **defaults** merge **`http://localhost:{5173|5174}/`** and **`http://127.0.0.1:{5173|5174}/`** for Hosted UI callback + sign-out URLs. **Full** [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) auth jobs require **`GOOGLE_OAUTH_*`** and package PreSignUp on prod deploy. **Student SPA:** [`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts) **`loginWith.email: true`** + OAuth domain; register/verify/forgot routes. **`npm run build:all`** enforces **`VITE_COGNITO_DOMAIN`** when pool + client ids are set ([`scripts/check-cognito-spa-env.mjs`](scripts/check-cognito-spa-env.mjs)). Operator notes: [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md). Child plan: [`plans/ui-overhaul/rs-6-email-password.md`](plans/ui-overhaul/rs-6-email-password.md).
- **Quality:** GitHub Actions (frontend ESLint + Knip + production build + Vitest, Lambda compile + Vulture + Radon informational, YAML parse for app + IAM bootstrap templates, import boundaries); **`npm run test:coverage`** is **local-only** (**`@vitest/coverage-v8`**, **`vitest run --coverage`**); plain **`npm run test`** stays non-instrumented ([`vitest.config.ts`](frontend/vitest.config.ts)). CORS hardened (Lambda + GatewayResponses + S3 bucket CORS); presigned upload **Content-Type** checks, **course-scoped S3 key** playback presign, conditional **`videoKey`** write, **API abuse protection** (RDS route limits + API Gateway throttles — see [ADR-0012](plans/architecture/adr-0012-api-abuse-protection.md)), SPA CloudFront **response headers** (HSTS / nosniff / frame deny), video bucket **Block Public Access** + **SSE-S3**.
- **Ops (IAM, outside Actions):** GitHub OIDC deploy role bootstrapped with [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) + [`scripts/deploy-github-iam-stack`](scripts/deploy-github-iam-stack.sh) (see [`infrastructure/README.md`](infrastructure/README.md)); not part of the **CI** or **Deploy** workflows. Backend inline policy scopes **CloudFormation / Lambda / DynamoDB / logs** to **`StreamMyCourse-*`** where feasible; SPA deploy workflows use **explicit** `workflow_call` secret maps—**re-sync** [`iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) / the stack template to the live role after edits (account-specific ARNs in the JSON).
- **Deploy topology:** **Prod-only** AWS — no mirrored dev stacks; local Vite proxies to prod API/Cognito ([`design.md` §10](./design.md)); legacy `*-dev` teardown in [`infrastructure/README.md`](infrastructure/README.md) Phase 0.

---

## Bridge to Phase 2 (recommended order)

Do these before or in parallel with heavy Phase 2 (payments / DRM) scope; aligns with [design.md §13](./design.md) and [ImplementationHistory.md](./ImplementationHistory.md).

| Order | Track | Outcome |
|-------|--------|---------|
| 1 | **Video provider hardening** | **Shipped baseline:** provider port + Kinescope default + webhook/DRM callbacks in catalog API. **Phase 2+:** edge signing/WAF/cost tuning, stronger webhook provenance controls, and explicit rollout policy if provider default changes. |
| 2 | **Static hosting** | **Shipped:** dual SPAs on S3 + CloudFront + custom domain (**prod**); ongoing = polish, monitoring, cost tuning. |
| 3 | **Auth** | **Shipped:** Cognito + Google IdP; **student** Google + email/password + **`PATCH /users/me`** + PreSignUp + Zoho CustomEmailSender; **teacher** Google-only; gateway authorizer; terms gate; integration test [`test_native_signup_profile.py`](tests/integration/test_native_signup_profile.py). **Next:** policy on which reads stay public vs token-required. |
| 4 | **RDS PostgreSQL (catalog)** | **Live in deployed prod:** [`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) (includes in-VPC **`StreamMyCourse-RdsSchemaApplier-prod`** fed from S3 zip built in CI) + api-stack `RdsStackName` parameter (required) + pipeline jobs (`deploy-rds-prod` / `apply-schema-prod` / `verify-prod-rds`, in [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)) + [`tests/integration/test_rds_path.py`](tests/integration/test_rds_path.py). See [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md). |
| 5 | **Security scanning in CI/deploy** | **Shipped baseline:** **[`ci.yml`](.github/workflows/ci.yml)** includes a `Security scans` gate: `npm audit --audit-level=high`, **Checkov** CloudFormation scanning via [`.checkov.yaml`](.checkov.yaml), **pip-audit** on Python requirement files, and **Gitleaks** Git secret scanning via [`.gitleaks.toml`](.gitleaks.toml). **Ongoing:** remove Checkov baseline skips as hardening items ship and expand dependency policy/SBOM depth as needed. |
| 6 | **Automated dependency upgrades (daily)** | Run **Dependabot**, **Renovate**, or equivalent on a **daily** schedule for **npm** (`frontend/`), **Python** (`infrastructure/lambda/catalog` / lock or requirements discipline), and **GitHub Actions** pin bumps; define policy for human review vs auto-merge (e.g. patch/minor vs major). |

Optional parallel work: richer `contracts` typing at the HTTP boundary.

---

## Phase 2: Monetization & Engagement (Weeks 5-8)

### Features

| Feature | Description | Complexity |
|---------|-------------|------------|
| **Provider reliability & DRM hardening** | Expand telemetry, retries, and policy controls around the shipped Kinescope integration | High |
| **Stripe Payments** | One-time purchases + subscriptions | High |
| **Reviews & Ratings** | 5-star + text reviews per course | Medium |
| **Watchlist** | Save courses for later | Low |
| **Progress Tracking v2** | % complete, lesson completion markers | Medium |
| **Instructor Analytics** | Views, revenue, enrollment charts | Medium |
| **Email Notifications** | SES for welcome, purchase confirmations | Medium |
| **1080p Transcoding** | Add 1080p quality tier | Low |
| **Quality Selector** | Manual quality override in player | Low |

### New Services
- **No new video vendor required for this phase baseline:** Kinescope integration is already in the shipped path; Phase 2 focuses on hardening/operations and optional multi-provider strategy.
- **RDS PostgreSQL:** Payments, subscriptions, analytics (ACID required) — **catalog already on RDS in deployed prod**; Phase 2 extends the schema with `payments` / `subscriptions` / `reviews` / `daily_stats` tables (see [Appendix: Full Data Models](#appendix-full-data-models)).
- **SES:** Transactional emails
- **Stripe:** Payment processing
- **ElastiCache (Optional):** Session caching if auth latency becomes issue

### Architecture Changes
```
Existing MVP +
  │
  ├── Existing Kinescope provider baseline (already shipped in catalog)
  │   ├── Upload init: `POST /upload-url` -> provider adapter
  │   ├── Playback: `GET /playback/...` -> provider payload (`videoId` + `drmAuthToken`)
  │   └── Webhooks: `/webhooks/kinescope` + `/webhooks/kinescope/drm-auth`
  ├── RDS PostgreSQL (Payments, analytics)
  ├── SES (Email notifications)
  └── Stripe Webhooks → Lambda
```

---

## Phase 3: Scale & Admin (Weeks 9-12)

### Features

| Feature | Description | Complexity |
|---------|-------------|------------|
| **Admin Panel** | User mgmt, course moderation, refunds | High |
| **Full-Text Search** | OpenSearch for course discovery | High |
| **Certificates** | PDF completion certificates | Medium |
| **Batch Uploads** | Multiple lessons at once | Medium |
| **WebSocket API** | Real-time upload progress, future live chat | Medium |
| **WAF** | DDoS protection, advanced security rules | Low — deferred (RDS + API GW limits shipped; see [ADR-0012](plans/architecture/adr-0012-api-abuse-protection.md)) |
| **Geo-blocking** | Regional content restrictions | Low |

### New Services
- **OpenSearch:** Full-text search index
- **WebSocket API Gateway:** Real-time features
- **WAF:** Web Application Firewall
- **Kinesis Firehose:** Player analytics streaming

### Architecture Changes
```
Phase 2 +
  │
  ├── OpenSearch (Search cluster)
  ├── WebSocket API Gateway
  ├── WAF (CloudFront + API Gateway)
  └── Kinesis Firehose → S3 → Athena (Analytics)
```

---

## Phase 4: Enterprise & Advanced (Months 4-6)

### Features

| Feature | Description | Complexity |
|---------|-------------|------------|
| **Live Streaming** | Elemental MediaLive integration | Very High |
| **Mobile Apps** | React Native or Flutter | High |
| **Offline Downloads** | DRM-protected downloads | Very High |
| **White-label** | Multi-tenant for partners | High |
| **AI Moderation** | AWS Rekognition for content | Medium |
| **Advanced Analytics** | ML-powered recommendations | High |
| **Team/Org Accounts** | B2B multi-seat licenses | Medium |

### New Services
- **Elemental MediaLive:** Live streaming
- **MediaPackage:** Live stream packaging
- **Rekognition:** Content moderation
- **SageMaker:** Recommendation engine
- **Multi-region:** Global expansion

---

## Full Architecture (All Phases)

```
┌─────────────────────────────────────────────────────────────────┐
│                        REACT FRONTEND                            │
│         (Web + Future: React Native iOS/Android)                 │
│                    Hosted: CloudFront + S3                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AMAZON CLOUDFRONT                         │
│           (CDN + WAF + Geo-blocking + Signed URLs)             │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        │                                           │
        ▼                                           ▼
┌───────────────┐                      ┌──────────────────────┐
│   S3 Buckets  │                      │   AWS API GATEWAY    │
│  (Video,      │                      │   REST + WebSocket   │
│   Thumbnails, │                      └──────────┬───────────┘
│   Static)     │                                 │
└───────────────┘                                 ▼
                                    ┌─────────────────────────┐
                                    │  Lambda + Fargate       │
                                    │  (Microservices)        │
                                    └───────────┬─────────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │                           │                           │
                    ▼                           ▼                           ▼
           ┌─────────────┐            ┌──────────────┐          ┌─────────────┐
           │  DynamoDB   │            │    RDS       │          │ ElastiCache │
           │ (Users,     │            │  PostgreSQL  │          │  (Redis)    │
           │  Progress,  │            │  (Payments,  │          │  (Sessions) │
           │  Catalog)   │            │  Analytics)  │          └─────────────┘
           └─────────────┘            └──────┬───────┘
                                           │
                                           ▼
                              ┌─────────────────────┐
                              │   OpenSearch        │
                              │   (Full-text)       │
                              └─────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
           ┌─────────────┐      ┌─────────────────┐    ┌─────────────┐
           │  SQS / SNS   │      │  AWS Cognito    │    │   SES       │
           │  (Async)     │      │  (Auth)         │    │  (Email)    │
           └──────┬──────┘      └─────────────────┘    └─────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │  Elemental MediaConvert   │
    │  (On-demand transcoding)  │
    └─────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │  Elemental MediaLive    │
    │  (Future: Live stream)  │
    └─────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │  Kinesis Firehose       │
    │  (Analytics pipeline)   │
    └─────────────────────────┘
```

---

## Technology decisions (cross-phase)

This table mixes **shipped MVP** choices with **Phase 2+ direction**. A “Chosen” cell is not always a dependency in today’s `package.json`—see MVP baseline above and [design.md §8](./design.md) for the current SPA stack.

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| **Auth** | Cognito vs Auth0 vs Clerk | Cognito | AWS native, cost-effective |
| **Data strategy (auth vs payments)** | DynamoDB-only vs split stores | DynamoDB for profiles/roles now; RDS for payments in Phase 2 | DynamoDB fits auth and catalog; PostgreSQL adds ACID for Stripe, refunds, and reporting when monetization ships |
| **Video Player** | Video.js vs hls.js vs DPlayer | **MVP:** native HTML5 `<video>` for MP4. **Phase 2+:** hls.js (or similar) if HLS or adaptive bitrate is required | Matches shipped MP4-only path; hls.js is a natural fit when streaming format moves beyond progressive MP4 |
| **State** | Redux vs Zustand vs Jotai | **MVP:** React component state plus [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) (`fetch`); no Zustand in-tree. **Phase 2+:** Zustand (or similar) if UI complexity warrants; TanStack Query only with an ADR | Keeps MVP small; avoid parallel data stacks until needed |
| **CSS** | Tailwind vs MUI vs Chakra | Tailwind | Customizable, smaller bundle |
| **Forms** | Formik vs RHF | **MVP:** lightweight controlled inputs where needed. **Phase 2+:** RHF + Zod if forms and validation grow | RHF + Zod are a strong default when form surface area expands; not required for the current MVP screens |
| **Transcoder** | MediaConvert vs FFmpeg self-hosted | MediaConvert | Serverless, no ops |
| **Search** | OpenSearch vs Algolia vs Typesense | OpenSearch | AWS native, cost at scale |
| **Payments** | Stripe vs PayPal vs Square | Stripe | Developer experience |
| **Mobile** | React Native vs Flutter | TBD | Team expertise decides |

---

## Cost Projections (Full Architecture)

Rough order-of-magnitude only; actual spend depends on egress, video minutes, and third-party vendors (e.g. Kinescope).

| Phase | Users | Est. Monthly Cost | Notes |
|-------|-------|-------------------|--------|
| MVP (current) | Pilot / low traffic | **~$0–20** typical on free tier + low egress | Matches [design.md](./design.md) success metrics; rises with S3/API usage |
| Phase 2 | 1K | ~$300-500 | Adds payments stack, email, richer video |
| Phase 3 | 10K | ~$2K-4K | Search, WAF, scale |
| Phase 4 | 50K+ | ~$8K-15K | Live, mobile, ML features |

*(Earlier single-row “MVP ~$100-200” was misleading for the current serverless MVP; treat that band as a **small production** footprint with meaningful video egress, not the first demo.)*

---

## Open Questions for Future Phases

1. **Live streaming in V1 or V2?** Adds ~4 weeks complexity.
2. **Single-tenant vs multi-tenant?** White-label adds architecture complexity.
3. **Mobile apps planned?** Share backend or separate?
4. **Content moderation:** Automated (Rekognition) or human-only?
5. **Offline downloads?** DRM complexity vs user value.

---

## Appendix: Full API Spec

See design.md for MVP APIs. Additional endpoints for future phases:

### Payments (Phase 2)
```
POST /payments/intent              # Stripe PaymentIntent
POST /payments/webhook             # Stripe webhook
GET  /payments/history
POST /subscriptions                # Create subscription
PUT  /subscriptions/{id}/cancel    # Cancel subscription
```

### Reviews (Phase 2)
```
GET  /courses/{id}/reviews
POST /courses/{id}/reviews
PUT  /reviews/{id}                 # Edit own review
DELETE /reviews/{id}
```

### Watchlist (Phase 2)
```
GET  /me/watchlist
POST /me/watchlist/{courseId}
DELETE /me/watchlist/{courseId}
```

### Admin (Phase 3)
```
GET  /admin/users
PUT  /admin/users/{id}/status      # suspend/activate
GET  /admin/courses?status=pending
PUT  /admin/courses/{id}/moderate  # approve/reject
GET  /admin/analytics
POST /admin/refunds
```

### Search (Phase 3)
```
GET /search?q=keyword&category=&sort=
GET /search/suggestions?q=partial
```

---

## Appendix: Full Data Models

### RDS PostgreSQL (Phase 2+)

```sql
-- Payments
CREATE TABLE payments (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    course_id VARCHAR(255),
    stripe_payment_intent_id VARCHAR(255),
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50),
    type VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Subscriptions
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    stripe_subscription_id VARCHAR(255),
    plan_type VARCHAR(50),
    status VARCHAR(50),
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reviews (with moderation)
CREATE TABLE reviews (
    id UUID PRIMARY KEY,
    course_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    content TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Analytics (time-series)
CREATE TABLE daily_stats (
    course_id VARCHAR(255),
    date DATE,
    views INTEGER DEFAULT 0,
    unique_viewers INTEGER DEFAULT 0,
    revenue_cents INTEGER DEFAULT 0,
    PRIMARY KEY (course_id, date)
);
```

---

*End of Roadmap Document*
