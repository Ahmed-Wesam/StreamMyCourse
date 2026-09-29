# StreamMyCourse — Module map (Lambda package)

This document is the “public surface” map for the Python Lambda under `infrastructure/lambda/catalog/`.

Related ADRs: [0011 video provider / Kinescope](./adr-0011-video-provider-port-kinescope-cutover.md), [0012 API abuse protection](./adr-0012-api-abuse-protection.md), [0013 purchases / bundle entitlements](./adr-0013-one-time-purchases-bundle-entitlements.md), [0014 student Google + SRP / Zoho](./adr-0014-student-google-cognito-srp-zoho-mail.md).

## Composition / entry

| Module | Responsibility | Public API |
|--------|----------------|------------|
| `index.py` | Lambda entrypoint | `lambda_handler`; rate-limit + session middleware; routes HTTP and **internal** invoke events (video edge, billing fulfillment hooks) |
| `bootstrap.py` | Dependency wiring (composition root) | `lambda_bootstrap()` — wires RDS repos/services when DB config is complete; adapters for cross-context ports (quiz visibility, course access, certificate entitlement, etc.) |
| `config.py` | Environment configuration | `load_config()`; `pick_origin` helpers live in `services/common/http.py` |

## Bounded contexts

### `services/course_management/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Parses API Gateway events; public course/lesson reads; mutations; **RS-11** lesson file routes |
| `service.py` | Domain/application | Business rules; ports only; playback + DRM auth; module quiz visibility merge; lesson files |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | `CourseCatalogRepositoryPort` |
| `storage.py` | Infrastructure adapter | S3 presign (video/thumbnail + **`LessonFileStorage`**) |
| `s3_common.py` | Shared S3 key/content-type helpers | Lesson file key shapes and validation |
| `ports.py` | Contracts | Repo/storage Protocols; `ModuleQuizVisibilityPort`; lesson-file ports |
| `models.py` | Domain models | `Course`, `CourseModule`, `Lesson`, `LessonFile`, `PresignResult` |
| `contracts.py` | API DTOs | TypedDicts for JSON shapes |
| `video_providers/` | Provider port + adapters | See ADR 0011 — `port.py`, `kinescope_adapter.py`, `s3_video_provider.py`, `vdocipher_adapter.py` |
| `internal_video.py` | Internal invoke bridge | Catalog handlers for video-provider-edge events |
| `video_webhooks.py` | HTTP adapter helpers | Kinescope webhook / drm-auth entry shapes |
| `image_storage.py` | Infrastructure | Course/lesson image presign helpers |

**Cross-context rule:** `course_management` must not import `services.auth` (enforced in CI).

**Sibling (not in this package):** `infrastructure/lambda/video_provider_edge/` — no-VPC Kinescope HTTP (ADR 0011).

### `services/auth/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | `GET` / `PATCH /users/me` |
| `service.py` | Domain/application | Profile + allowlists; depends on `UserProfileRepositoryPort` |
| `ports.py` | Contracts | `UserProfileRepositoryPort` |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | `UserProfileRdsRepository` |
| `session.py` | Middleware helper | Student single-session vs RDS (`session_superseded`) |
| `profile_allowlists.py` | Domain | Country / profession allowlists (RS-6) |

**Cross-context rule:** `auth` must not import `course_management` (enforced in CI). Cognito Admin/IdP calls stay **out** of this package (ADR 0014).

### `services/enrollment/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `ports.py` | Contracts | `EnrollmentRepositoryPort` |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | Idempotent upserts via `ON CONFLICT DO NOTHING` |

Enrollment rows do **not** grant lesson access under RS-5 (purchases do); table retained for history/analytics. See [adr-enrollment-course-access.md](./adr-enrollment-course-access.md) and ADR 0013.

### `services/progress/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | `GET /courses/{id}/progress`, `PUT /courses/{id}/lessons/{id}/progress` |
| `service.py` | Domain/application | Authorization, auto-complete ratio, position validation |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | ON CONFLICT UPDATE upserts |
| `ports.py` | Contracts | `LessonProgressRepositoryPort` |
| `contracts.py` | API DTOs | `CourseProgressResponse`, `LessonProgressItem` |

**Cross-context rule:** `progress` may use enrollment/access ports but must not import `course_management` directly for persistence.

### `services/question_banks/` (implemented)

| File | Layer | Notes |
|------|-------|-------|
| `models.py` | Domain | Banks, module quizzes, questions, bindings, attempts |
| `ports.py` | Contracts | Authorizer + student lesson-access / course-read ports (no `course_management` import) |
| `service.py` | Domain/application | Publisher CRUD/publish; student start/submit; grading orchestration |
| `controller.py` | HTTP adapter | Publisher + student quiz routes (`quiz/submit` before `quiz/start` before bare `quiz`) |
| `contracts.py` | API DTOs | Start/submit discriminated payloads; student-safe question DTOs |
| `binding_draw.py` / `presentation_shuffle.py` / `grading.py` / `visibility.py` / `gating.py` | Domain (pure) | Draw, shuffle, grade, visibility, module lock helpers |
| `rds_repo.py` | Persistence adapter | Banks, quizzes, questions, bindings, attempts, submissions |

**Cross-context rule:** `question_banks` must not import `course_management` or `auth`.

### `services/purchases/` (implemented — RS-5)

| File | Layer | Notes |
|------|-------|------|
| `service.py` | Domain | `CourseAccessService.has_course_access` — paid course or paid bundle; owner/admin bypass |
| `checkout_service.py` / `manage_service.py` | Application | Checkout precheck; bundle/course price manage |
| `controller.py` | HTTP adapter | `POST /billing/checkout-session`, `GET /billing/bundle`, `GET /billing/purchases`, price/bundle PATCH routes |
| `internal_checkout.py` | Internal | Fulfillment-facing helpers invoked from billing queue path |
| `repo.py` | Persistence | `purchases`, `bundle_offers`, course price |
| `ports.py` / `models.py` | Contracts / domain | Purchase repository Protocol and models |

**Supersedes** subscription module / `access-policy-v1` subscription rules (ADR 0013).

**Sibling:** `infrastructure/lambda/billing_edge/` — no-VPC PayTabs session + IPN → SQS events (`purchase.paid|failed|revoked`).

### `services/billing_merchant/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Teacher merchant setup / checklist |
| `service.py` | Domain/application | Checklist + profile-id placeholder rules |
| `repo.py` | Persistence | Merchant account rows in RDS |

### `services/contact/` (implemented — RS-10)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Public `POST /contact` (no JWT) |
| `service.py` | Application | Validate → enqueue transactional-mail SQS (Zoho worker sends) |
| `validation.py` / `models.py` | Edge / domain | Payload parse; honeypot `rs_hp` → 202 without enqueue |

Rate limits: `contact.ip` / `contact.global` (ADR 0012). Catalog never calls Zoho SMTP.

### `services/lesson_notes/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Student/teacher lesson notes CRUD |
| `service.py` | Domain/application | Access-gated notes |
| `rds_repo.py` / `ports.py` / `contracts.py` / `models.py` / `validation.py` | Persistence + DTOs | RDS-backed notes |

Lesson **file attachments** (RS-11) live under **`course_management`** (`LessonFile` + `LessonFileStorage`), not this folder.

### `services/assignments/` (implemented — RS-13)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Assignment CRUD, submissions, instruction images |
| `service.py` | Domain/application | Gating, grading notify enqueue |
| `rds_repo.py` / `storage.py` | Persistence / S3 | Submissions + instruction image keys |
| `ports.py` / `contracts.py` / `models.py` / `validation.py` | Contracts + DTOs | Typed boundaries |

### `services/certificates/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Issue/list + public verify |
| `service.py` | Domain/application | Eligibility + issue |
| `entitlement.py` / `eligibility.py` / `credential_id.py` | Domain (pure) | Purchase/activity entitlement; issue rules; ids |
| `rds_repo.py` / `ports.py` / `contracts.py` / `models.py` | Persistence + DTOs | Certificate rows |

Public verify uses rate-limit policies `certificate.verify.*` (ADR 0012). PDF is client-side (no server PDF / no NAT).

### `services/research_team/` (implemented — RS-14)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Requirements + apply routes |
| `service.py` | Domain/application | Eligibility and application rules |
| `rds_repo.py` / `ports.py` / `contracts.py` / `models.py` | Persistence + DTOs | Research-team tables |

Rate limits: `research_team.requirements.*`, `research_team.apply` (ADR 0012).

### `services/rate_limit/` (implemented — ADR 0012)

| File | Layer | Notes |
|------|-------|------|
| `policies.py` | Domain | Per-route policy table + actor resolution |
| `service.py` | Application | Check/increment |
| `rds_repo.py` / `ports.py` / `models.py` | Persistence | Counter store |
| `http.py` | Adapter helpers | 429 / fail-closed 503 responses; `rate_limit_denied` logging |

Wired as middleware from `index.py`. Optional `RATE_LIMIT_MAX_OVERRIDES` in `config.py`.

### `services/common/` (shared kernel)

Cross-cutting utilities shared by multiple contexts:

- `errors.py` — typed HTTP errors (`HttpError` hierarchy)
- `http.py` — CORS + JSON response helpers; authorizer claim extraction
- `validation.py` — strict JSON parsing + simple validators
- `sqs_client.py` — enqueue async jobs (media cleanup, transactional mail, billing) via boto3 SQS
- `playback_watermark.py` — Kinescope watermark text from Cognito claims

## Edge / worker packages (outside catalog `services/`)

| Package / stack | Role |
|-----------------|------|
| `infrastructure/lambda/video_provider_edge/` | Kinescope HTTP (no VPC) — ADR 0011 |
| `infrastructure/lambda/billing_edge/` | PayTabs HPP / IPN → SQS — ADR 0013 |
| `infrastructure/lambda/transactional_mail/` | Zoho SMTP consumer — contact + notify; same secret posture as CustomEmailSender |
| `infrastructure/lambda/media_cleanup/` | Async S3 deletes after course/media delete |
| `infrastructure/lambda/cognito_pre_signup/` | Account linking / duplicate email — ADR 0014 |
| `infrastructure/lambda/cognito_custom_email_sender/` | Cognito → Zoho mail — ADR 0014 |
| `infrastructure/lambda/cognito_user_profile_sync/` | PreTokenGeneration session sync + profile sync (out of VPC) |

## What other modules may import

- Controllers may import `services/common/*` and their own `contracts.py`.
- Services may import `ports.py`, `models.py`, and `services/common/errors.py` (not HTTP helpers). They may call `sqs_client.send_*` helpers for enqueue paths (no HTTP imports).
- Repos/storage may import `boto3` and S3/Dynamo specifics where still present.
- `rds_repo.py` modules may import `psycopg2`; no other module may (enforced in CI).
- `bootstrap.py` may import both `boto3` (Secrets Manager) and `psycopg2` (connection) — it is the composition root.
- Leaf contexts must not import sibling contexts’ concrete modules; cross-context ports are wired in `bootstrap.py`.

## Enforcement

- Cursor rule: `.cursor/rules/clean-architecture-boundaries.mdc`
- CI script: `scripts/check_lambda_boundaries.py` (runs in GitHub Actions)
- Auth skill: `.cursor/skills/auth-no-cognito-in-vpc/SKILL.md` (no Cognito from catalog)
