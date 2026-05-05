# StreamMyCourse — Full Architecture Roadmap

> **Status:** **Post-MVP evolution** (MVP baseline shipped; Phase 2+ ahead) · **Last updated:** 2026-05-04

This document is the **long-range** product and architecture vision (Phase 2 onward). The current **MVP contract** (what is built, APIs, data model, deployment) lives in [design.md](./design.md). **Near-term engineering priorities** (CloudFront, SPA hosting, auth) are listed there as §13 and mirrored below so this file stays navigable without opening multiple docs.

**Engineering bar (post-MVP):** Ship **clean, intentional implementations**—prefer **documented component APIs** and a **single embedded surface** ([`frontend/src/components/auth/SignIn.tsx`](frontend/src/components/auth/SignIn.tsx)): **Tailwind** Google CTA + **`signInWithRedirect`** (`aws-amplify/auth`), with **`AuthenticatorProvider`** / **`useAuthenticator`** for Hub-driven session state—**no** Amplify `<Authenticator>` widget or CSS that hides username/password fields. Regression coverage in **[`SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx)** (Testing Library + jsdom).

---

## MVP baseline (shipped)

Roughly what exists today before Phase 2 work:

- **Frontend:** React 19 (Vite + TS + Tailwind), catalog + lesson player + instructor dashboard and course management. **Hosted** as **two SPAs** (student + teacher) on S3 + CloudFront + Route 53 via **`StreamMyCourse-EdgeHosting-{env}`** in **`us-east-1`** (unified stack). On **`main`**, **[`deploy-backend.yml`](.github/workflows/deploy-backend.yml)** drives dev/prod SPA asset deploys after edge (with **[`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml)** / teacher reusable).
- **API:** API Gateway REST → single Python Lambda (`infrastructure/lambda/catalog/`), layered **controller → service → repo** with `plans/architecture/` ADRs and CI boundary checks. **CI** then **Deploy** ([`deploy-backend.yml`](.github/workflows/deploy-backend.yml) after green [`ci.yml`](.github/workflows/ci.yml)) runs video + API + edge + SPAs via [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) / reusable web workflows: **prod** backend and both prod SPAs wait for **integ**, **integ tests**, **dev edge**, **dev backend**, **both dev SPAs**, and **prod edge**; **prod edge** still starts in parallel with dev app jobs after integ + dev edge only.
- **Data:** **RDS PostgreSQL** is the **live catalog** in **deployed dev/prod** (`USE_RDS=true`) — [`infrastructure/templates/rds-stack.yaml`](infrastructure/templates/rds-stack.yaml), Lambda VPC + `DB_*` wiring in [`api-stack.yaml`](infrastructure/templates/api-stack.yaml), `services/<context>/rds_repo.py`, migrations under [`infrastructure/database/migrations/`](infrastructure/database/migrations/). **DynamoDB** single-table catalog (`StreamMyCourse-Catalog-{env}`) is **deprecated** in those environments (**unused** for app traffic); the DynamoDB repos remain for **local / emergency rollback** only ([ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md)). S3 presigned **SigV4** uploads; lesson playback and thumbnails use **CloudFront signed URLs** when signing is configured (**SSM** public PEM + **Secrets Manager** private key + [`cloudfront-keys-stack.yaml`](infrastructure/templates/cloudfront-keys-stack.yaml)), otherwise **S3 presigned GET** fallback; **video** stack provisions **CloudFront + OAC**, **`CfInvalidate` Lambda**, and optional **Trusted Key Groups** (see `design.md` §5 / §13).
- **Auth (optional on API):** Cognito user pool via CloudFormation (`StreamMyCourse-Auth-<env>`); API authorizer when the pool ARN is passed on backend deploy. **Auth template** ([`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml)) is **Google-federation-only**: **`GoogleClientId` / `GoogleClientSecret`** are required; student/teacher app clients use **`SupportedIdentityProviders: [Google]`** only. **Full** [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) auth jobs require GitHub secrets **`GOOGLE_OAUTH_CLIENT_ID`** and **`GOOGLE_OAUTH_CLIENT_SECRET`** (fail-fast step) and pass them on every auth deploy; [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1) **`-Template auth`** enforces the same locally. **Hosted student + teacher SPAs** use **[`SignIn.tsx`](frontend/src/components/auth/SignIn.tsx)** (see [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md)). **`npm run build:all`** enforces **`VITE_COGNITO_DOMAIN`** whenever pool + client ids are set ([`scripts/check-cognito-spa-env.mjs`](scripts/check-cognito-spa-env.mjs)). **Runtime parity:** Amplify configures **Hosted UI OAuth only** — [`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts) treats Cognito as configured only when **pool id, client id, and `VITE_COGNITO_DOMAIN`** are non-empty (no native Amplify **`loginWith.email`**). GitHub Environment secrets from stack outputs ([`scripts/set-github-auth-secrets-from-stack.ps1`](scripts/set-github-auth-secrets-from-stack.ps1) or [`scripts/print-auth-stack-outputs.ps1`](scripts/print-auth-stack-outputs.ps1) / [`.sh`](scripts/print-auth-stack-outputs.sh)); local dev needs the same trio in `frontend/.env` to exercise Hosted UI flows. **Operator hygiene:** `TEACHER_COGNITO_CALLBACK_URLS` / `LOGOUT_URLS` (and student equivalents) must list each deployed SPA origin with a **trailing slash** (matches `frontend/src/lib/auth.ts`); [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) and [`infrastructure/deploy-environment.ps1`](infrastructure/deploy-environment.ps1) pass **`CorsAllowOrigin`** CSV including **teacher** domains. API stack deployment description includes the Lambda zip key so **API Gateway** republishes when the catalog artifact changes (avoids stage/authorizer drift).
- **Quality:** GitHub Actions (frontend ESLint + Knip + production build + Vitest, Lambda compile + Vulture + Radon informational, YAML parse for app + IAM bootstrap templates, import boundaries); CORS hardened (Lambda + GatewayResponses + S3 bucket CORS); presigned upload **Content-Type** checks, **course-scoped S3 key** playback presign, conditional **`videoKey`** write, API stage throttling, SPA CloudFront **response headers** (HSTS / nosniff / frame deny), video bucket **Block Public Access** + **SSE-S3**.
- **Ops (IAM, outside Actions):** GitHub OIDC deploy role bootstrapped with [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) + [`scripts/deploy-github-iam-stack`](scripts/deploy-github-iam-stack.sh) (see [`infrastructure/README.md`](infrastructure/README.md)); not part of the **CI** or **Deploy** workflows. Backend inline policy scopes **CloudFormation / Lambda / DynamoDB / logs** to **`StreamMyCourse-*`** where feasible; SPA deploy workflows use **explicit** `workflow_call` secret maps—**re-sync** [`iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) / the stack template to the live role after edits (account-specific ARNs in the JSON).

---

## Bridge to Phase 2 (recommended order)

Do these before or in parallel with heavy Phase 2 (payments / DRM) scope; aligns with [design.md §13](./design.md) and [ImplementationHistory.md](./ImplementationHistory.md).

| Order | Track | Outcome |
|-------|--------|---------|
| 1 | **Video CDN** | **Shipped:** CloudFront + OAC + signed URLs path ([`video-stack.yaml`](infrastructure/templates/video-stack.yaml), [`cloudfront_storage.py`](infrastructure/lambda/catalog/services/course_management/cloudfront_storage.py), bootstrap wiring); SSM-held public key; private key in Secrets Manager (`deploy-cloudfront-keys-stack`); invalidate-on-media-change. **Phase 2:** WAF, cost tuning, shorter TTL experiments. |
| 2 | **Static hosting** | **Shipped:** SPA on S3 + CloudFront + custom domain per env; ongoing = polish, monitoring, cost tuning. |
| 3 | **Auth** | **Shipped:** Cognito + required Google IdP + Google-only public SPA clients; gateway authorizer + profile route; build-time **and** SPA runtime Hosted UI domain contract; **`SignIn`** shell + Vitest coverage. **Next:** policy on which reads stay public vs token-required. |
| 4 | **RDS PostgreSQL (catalog)** | **Live in deployed dev/prod:** [`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) (includes in-VPC **`StreamMyCourse-RdsSchemaApplier-<env>`** fed from S3 zip built in CI) + api-stack **`UseRds=true`** + pipeline jobs (`deploy-rds-dev` / `apply-schema-dev` / `verify-dev-rds`, prod equivalents, in [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)) + [`tests/integration/test_rds_path.py`](tests/integration/test_rds_path.py). **DynamoDB catalog is deprecated** in managed dev/prod (unused). Emergency rollback to DynamoDB would be **`UseRds=false`** + `TABLE_NAME` only if a table still exists ([ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md)). |
| 5 | **Security scanning in CI/deploy** | Add **pipeline gates** for vulnerabilities, misconfigurations, and **secrets** (e.g. dependency/SBOM or OSV-style scans, IaC linters where templates warrant, secret scanning / leaked-credential checks) wired into **[`ci.yml`](.github/workflows/ci.yml)** and/or **[`deploy-backend.yml`](.github/workflows/deploy-backend.yml)** (or reusable workflows) so failures surface **before** dev/prod promotion—not only on developer machines. |
| 6 | **Automated dependency upgrades (daily)** | Run **Dependabot**, **Renovate**, or equivalent on a **daily** schedule for **npm** (`frontend/`), **Python** (`infrastructure/lambda/catalog` / lock or requirements discipline), and **GitHub Actions** pin bumps; define policy for human review vs auto-merge (e.g. patch/minor vs major). |

Optional parallel work: legacy DynamoDB access-pattern tuning if rollback ever runs, richer `contracts` typing at the HTTP boundary.

---

## Phase 2: Monetization & Engagement (Weeks 5-8)

### Features

| Feature | Description | Complexity |
|---------|-------------|------------|
| **Kinescope DRM** | Screen recording protection (OBS black screen), Widevine L3 | High |
| **Stripe Payments** | One-time purchases + subscriptions | High |
| **Reviews & Ratings** | 5-star + text reviews per course | Medium |
| **Watchlist** | Save courses for later | Low |
| **Progress Tracking v2** | % complete, lesson completion markers | Medium |
| **Instructor Analytics** | Views, revenue, enrollment charts | Medium |
| **Email Notifications** | SES for welcome, purchase confirmations | Medium |
| **1080p Transcoding** | Add 1080p quality tier | Low |
| **Quality Selector** | Manual quality override in player | Low |

### New Services
- **Kinescope:** Video hosting + DRM (€10/mo + usage, ~$50-80/mo total)
- **RDS PostgreSQL:** Payments, subscriptions, analytics (ACID required) — **catalog already on RDS in deployed dev/prod**; Phase 2 extends the schema with `payments` / `subscriptions` / `reviews` / `daily_stats` tables (see [Appendix: Full Data Models](#appendix-full-data-models)).
- **SES:** Transactional emails
- **Stripe:** Payment processing
- **ElastiCache (Optional):** Session caching if auth latency becomes issue

### Architecture Changes
```
Existing MVP +
  │
  ├── Kinescope (Video hosting + DRM, replaces S3/CloudFront for video)
  │   ├── Upload: Instructor → Kinescope API
  │   ├── Playback: Kinescope Player (white-label, DRM-protected)
  │   └── Webhooks: License validation, progress tracking, processing complete
  ├── RDS PostgreSQL (Payments, analytics)
  ├── SES (Email notifications)
  └── Stripe Webhooks → Lambda
```

### Kinescope Integration (Low-Level Design)

**Upload Flow:**
1. Frontend → POST `/instructor/upload-url` → Lambda → Kinescope presigned URL
2. Frontend → PUT upload URL (direct to Kinescope) → Kinescope transcodes + DRM encrypts
3. Frontend → POST `/instructor/courses/{id}/videos` → Lambda persists to the catalog store (RDS in deployed environments)
4. Kinescope webhook → POST `/webhooks/kinescope/ready` → Lambda updates status

**Streaming Flow:**
1. Frontend → GET `/courses/{courseId}/lessons/{lessonId}/player` → Lambda validates enrollment
2. Frontend → Kinescope Player SDK → Requests DRM license
3. Kinescope → POST `/webhooks/kinescope/license` → Lambda validates JWT + enrollment
4. License granted → Player decrypts + plays (OBS sees black screen)

**Webhook Endpoints:**
- `POST /webhooks/kinescope/license` — Validate user session before DRM license
- `POST /webhooks/kinescope/progress` — Track watch progress
- `POST /webhooks/kinescope/ready` — Video processing complete notification

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
| **WAF** | DDoS protection, advanced security rules | Low |
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
