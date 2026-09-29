# StreamMyCourse — MVP Design Document

> **Status:** The **MVP defined in this document is shipped** and running in **prod**. Further product scope, Phase 2 work, and the **engineering quality bar** (clean, maintainable code—prefer supported APIs over brittle UI hacks) are tracked in **[roadmap.md](./roadmap.md)** and **[ImplementationHistory.md](./ImplementationHistory.md)**. **Last updated:** 2026-09-25 · **Stack:** React 19 + AWS (Serverless) · **Frontend tests:** Vitest (optional **`npm run test:coverage`** — v8 only when `--coverage`; see **`frontend/vitest.config.ts`**).

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
| FR-6 | Catalog persistence: **RDS PostgreSQL** is the canonical store (`DB_*` + Secrets Manager from RDS stack). Lambda returns **503** `catalog_unconfigured` when RDS is not wired | Required |

**Out of scope:** Payments, enrollments, progress tracking, transcoding, DRM.

**In scope:** Instructor upload via presigned S3 URLs; draft/publish workflow backed by **PostgreSQL** in deployed environments (see §6).

---

## 3. MVP Architecture

```
React (Vite + TS + Tailwind)
        │
        ├── REST API via API Gateway → Lambda (Python): courses, lessons,
        │   publish, provider upload-url init, provider playback contract, webhooks
        │
        └── Kinescope-first video provider via ports (S3/VdoCipher adapters retained)
```

**Current Implementation:**
- Lambda package under `infrastructure/lambda/catalog/` (handler `index.lambda_handler`; not inline in YAML)
- **Modular layout (single deploy unit):** `services/course_management/` (controller → service → repo/storage), `services/common/` (HTTP/CORS helpers, validation, errors), `services/auth/` (user profile **`GET` / `PATCH /users/me`**); composition in `bootstrap.py`; entry in `index.py`
- **User profile rows (RDS):** `users` is upserted on every successful Cognito sign-in by a **PostAuthentication** Lambda shipped with [`auth-stack.yaml`](infrastructure/templates/auth-stack.yaml) when `EnableUserProfileSync` and RDS parameters are set (CI passes the RDS stack + S3 zip). The same row is also created/updated lazily via **`GET /users/me`**; extended fields (name, country, profession, terms/privacy timestamps) via **`PATCH /users/me`** ([`016_user_profile_fields.sql`](infrastructure/database/migrations/016_user_profile_fields.sql)). **POST /courses/{id}/enroll** always calls `get_or_create_profile` first so missing `users` rows cannot break the `enrollments` FK.
- **RDS PostgreSQL** catalog is the only persistence path; VPC-attached Lambda with `DB_HOST` / `DB_NAME` / `DB_PORT` / `DB_SECRET_ARN` from the api stack (see §10). DynamoDB path was removed; `RdsStackName` is required for api stack deploy
- S3 bucket CORS configured for browser PUT uploads
- API Gateway REST API with OPTIONS on routes; **GatewayResponses** for DEFAULT_4XX/5XX add CORS headers on error paths; stack parameter `CorsAllowOrigin` feeds Lambda `ALLOWED_ORIGINS`
- Video provider cutover uses `VIDEO_PROVIDER` (`kinescope` default) with typed playback responses from the same `GET /playback/{courseId}/{lessonId}` API contract

**MVP scope:** API-invoked Lambda only (no event sources). Cognito is **optional** (enabled only when the API stack receives a User Pool ARN). MediaConvert/CloudFront-video are Phase 2.

---

## 4. AWS Services (MVP)

| Service | Use | Cost Estimate |
|---------|-----|---------------|
| **CloudFront** | CDN for static + MP4 | **Deferred to Phase 2** |
| **S3** | Static + MP4 storage | Free tier friendly (direct access for MVP) |
| **API Gateway** | Minimal REST API | Free tier friendly |
| **Lambda** | Minimal API handler | Free tier friendly |
| **DynamoDB** | **Removed** — legacy single-table model was deprecated and is now fully removed. Existing tables may be orphaned (retained) until manual cleanup | None (unused) |
| **RDS PostgreSQL** | **Canonical catalog store**: courses, lessons, enrollments, user profiles, lesson progress ([`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml), migrations under [`infrastructure/database/migrations/`](infrastructure/database/migrations/)) | `db.t4g.micro` (eligible free tier when applicable) |
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
Teacher upload init → `POST /upload-url` → active provider (`VIDEO_PROVIDER`)
                    ↓
Kinescope upload + transcode status webhooks (`POST /webhooks/kinescope`)
                    ↓
Student playback contract (`GET /playback/{courseId}/{lessonId}`):
  - Kinescope: `{ provider: "kinescope", videoId, drmAuthToken, watermarkText }` — required `watermarkText` (viewer name from at least one of `given_name` or `family_name`, plus `email`, from Cognito authorizer claims; newline-separated; max 120 chars). Returns **403** `watermark_profile_incomplete` when `email` is missing or when **both** `given_name` and `family_name` are absent/blank.
  - S3: `{ provider: "s3", playbackUrl }`
```

- **Provider abstraction:** `services/course_management/video_providers/port.py` isolates provider-specific upload/playback/delete operations from domain flow.
- **Upload:** `POST /upload-url` initializes provider upload (optional `filesize` for Kinescope init) and persists the returned `videoKey` in lesson metadata (`pending`). Client upload: S3 presigned **PUT**; Kinescope **POST** binary to init `endpoint` (`uploadMethod`: `post` or `tus` for very large files).
- **Processing status:** webhook `POST /webhooks/kinescope` accepts `media.update.status`; `done` marks lesson `ready` (after Kinescope API status check when token configured), `error`/`aborted` marks `failed`.
- **Playback:** lesson playback route returns provider-discriminated payloads — Kinescope (`provider`, `videoId`, `drmAuthToken`, required `watermarkText` from authorizer claims via [`playback_watermark_from_claims`](infrastructure/lambda/catalog/services/common/playback_watermark.py); **403** when profile incomplete) or S3 (`provider`, `playbackUrl`).
- **DRM callback:** `POST /webhooks/kinescope/drm-auth` validates a signed token and current lesson access before returning `{ "allow": true|false }`.

---

## 6. Data (MVP)

**RDS PostgreSQL (deployed prod):** The managed **prod** API uses **only** the relational path (`USE_RDS=true`). Schema: [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) — tables `courses`, **`course_modules`** (sections; every lesson belongs to one module), **`lessons`** (`module_id` FK, `lesson_order` unique per course+module), `enrollments`, `users`, `lesson_progress` (see [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md), [ADR-0010](plans/architecture/adr-0010-lesson-progress-rds.md)). **`POST /courses`** inserts one default module (`module_order = 0`) in the same transaction as the course row. **DynamoDB catalog tables are deprecated** and are **not** used for application reads/writes.

**Misconfiguration:** When RDS is not wired (missing `RdsStackName` or incomplete DB env), catalog routes return **503** with `code: catalog_unconfigured` (OPTIONS still returns CORS preflight). When `ALLOWED_ORIGINS` is unset or parses to an empty allowlist, the handler returns **503** with `code: cors_misconfigured` and **no** `Access-Control-Allow-*` headers (fail-secure); set `ALLOWED_ORIGINS=*` only for deliberate local/dev tooling. Local UI must call a deployed API or a stack with persistence and CORS env set.

---

## 7. API Design (MVP)

### Courses
```
GET    /courses                          // List (published only for catalog); items may include thumbnailUrl (presigned GET) and **RS-7 card fields** when set: `level`, `estimatedHours`, `catalogSkills` (no section bodies)
POST   /courses                          // Create DRAFT course + default module (module_order 0)
GET    /courses/mine                     // Instructor dashboard: courses owned by caller (DRAFT + PUBLISHED); teacher/admin + Cognito when enforced; oldest-first (`created_at` ascending)
GET    /courses/{id}                     // Full details for catalog; may include thumbnailUrl + enrolled (bool). **RS-7:** same card fields plus optional marketing sections (`subtitle`, `problem`, `outcomes`, `inside`, `handsOn`, `highlights`, `audience`, `assessment`, `enrollCta`, `curriculumLead`) — omitted when empty. PUBLISHED is public, DRAFT is 404 unless caller is owner/admin (authz uses `sub`/`role` from API Gateway authorizer context when available).
PUT    /courses/{id}                     // Update title + description; optional body key **`page`** (JSON object) replaces stored marketing document when present (publisher only). Omitting `page` leaves `page_content` unchanged.
PUT    /courses/{id}/publish             // Publish (requires ≥1 ready lesson)
PUT    /courses/{id}/thumbnail-ready     // Body { thumbnailKey }; persist cover image after S3 PUT (see upload-url)
DELETE /courses/{id}                     // Delete course; CASCADE removes modules + lessons + related progress
POST   /courses/{id}/enroll              // Idempotent self-service enrollment (PUBLISHED only); Cognito when enforced
```

### Course modules (sections)
```
GET    /courses/{id}/modules             // List modules (order, title, description); public for PUBLISHED; DRAFT 404 unless owner/admin (same rule as lesson list). **QB-D + RS-8:** optional per-module `moduleQuiz` when visibility passes — `{ "available": true, "servedCountN": <n>, "passPercent": <1–100> }` (draw size + pass threshold; default **70** when stored; no question text); when the signed-in viewer has submitted attempts, also `latestScorePercent` (whole percent, rounded half away from zero, e.g. 2/3 → 67) and `passed` (true when **any** submission meets `passPercent`). **`locked`** (boolean): for enrolled students, true when an **earlier** module with a visible quiz is not passed; publisher/admin bypass (field false/absent). Omitted when course is DRAFT, viewer lacks lesson access (not enrolled and not publisher/admin), bank is not PUBLISHED, or `served_count_n` is unset.
POST   /courses/{id}/modules             // Create module (body: title, optional description); Cognito teacher/admin when enforced
POST   /courses/{id}/question-banks      // Create DRAFT question bank for course; body `{ "name": "..." }` where name is trimmed, non-empty, max 80 chars, and not required to be unique. Cognito teacher/admin; **course publisher** (or admin) only — same `courses.created_by` vs `sub` rule as other course mutations. **201** + `{ "questionBankId": "<uuid>", "name": "<trimmed name>" }`
GET    /courses/{id}/question-banks      // **QB-L:** List banks for course (publisher read). Cognito teacher/admin; **same publisher scope as GET modules on drafts** (404 `not_found` when course missing or caller cannot manage — not **403**). **200** JSON array of `{ "questionBankId", "name", "status", "createdAt", "updatedAt" }`; no banks → `[]`. **401** if unauthenticated when authorizer enforced.
PATCH  /courses/{id}/question-banks/{bid} // Rename a DRAFT or PUBLISHED question bank; body `{ "name": "..." }` with the same trim / non-empty / max-80 validation and no uniqueness constraint. Publisher-only; **200** `{ "questionBankId": "<uuid>", "name": "<trimmed name>" }`; unknown/wrong-bank → **404** `not_found`
GET    /courses/{id}/module-quizzes      // **QB-L:** List module quiz rows for the course (publisher read). Same Cognito + publisher **404** scope as `GET …/question-banks` (not **403**). **200** JSON array of `{ "quizId", "moduleId", "questionBankId", "servedCountN", "passPercent", "createdAt", "updatedAt" }` — **one element per `module_quizzes` row** (modules without a quiz row are omitted; aggregate **[]** when none). **401** if unauthenticated when authorizer enforced.
GET    /courses/{id}/question-banks/{bid}/questions  // **QB-L:** List questions in bank (publisher read; includes `correctOptionKey` where stored). Same auth/404 scope as `GET …/question-banks`. **200** JSON array of `{ "questionId", "status", "promptText", "optionsJson", "correctOptionKey" }` (stable order: `created_at`, then id). Wrong `bid` for course or no access → **404** `not_found` (not empty list). **401** if unauthenticated when authorizer enforced.
POST   /courses/{id}/question-banks/{bid}/questions  // **DRAFT:** add DRAFT MCQ row (`promptText`, `optionsJson`, optional `correctOptionKey` must match a choice key when set). **PUBLISHED:** append PUBLISHED MCQ (same body shape; **`correctOptionKey` required**). Publisher-only; **201** + `{ "questionId": "<uuid>" }`
PATCH  /courses/{id}/question-banks/{bid}/questions/{qid}  // Update **DRAFT** MCQ only (body requires ≥1 of `promptText`, `optionsJson`, `correctOptionKey`). **PUBLISHED** rows → **409** `conflict`. Publisher-only; **200** `{ "status": "updated" }`; unknown/wrong-bank id → **404** `not_found`
DELETE /courses/{id}/question-banks/{bid}/questions/{qid}  // Delete **DRAFT** MCQ only; **PUBLISHED** → **409** `conflict`. Publisher-only; **200** `{ "status": "deleted" }`; unknown/wrong-bank → **404** `not_found`
POST   /courses/{id}/question-banks/{bid}/publish     // Publish bank + set `served_count_n` on linked module quiz (body `n`, `moduleId`); requires module_quiz row with matching `questionBankId`; validates §9.3 / §5 (N ≥ 1, corpus ≥ N, each draft has designated correct key in `optionsJson`); **200** + `{ "status": "PUBLISHED" }`; republish **409** `conflict`
POST   /courses/{id}/modules/{mid}/quiz  // Create module quiz row; body **must** include `questionBankId` (non-empty UUID for an existing bank in this course). Optional `passPercent` (integer **1–100**, default **70**). Same publisher auth as bank create. Missing/blank/invalid → **400** `bad_request`; bank in another course → **400** `bad_request` (message references course). Module already has quiz → **409** `conflict`; question bank already linked to another module in this course → **409** `conflict` (message: question bank already linked to another module). **201** + `{ "quizId": "<uuid>" }`
PATCH  /courses/{id}/modules/{mid}/quiz  // **RS-8:** Update pass threshold; body `{ "passPercent" }` (integer **1–100**). Same publisher auth as create. **200** `{ "quizId", "passPercent" }`; no quiz row or wrong course → **404** `not_found`
GET    /courses/{id}/modules/{mid}/quiz/attempts  // **RS-8:** List the signed-in student’s **submitted** attempts for this module quiz (same visibility gate as start). **200** JSON array (oldest first): `{ "attemptId", "attemptNumber", "correctCount", "totalCount", "scorePercent", "passPercent", "passed", "submittedAt" }`; none → `[]`. **403** `module_locked` when the module is locked for this student. **401** if unauthenticated.
POST   /courses/{id}/modules/{mid}/quiz/start  // **QB-F + QB-G + QB-I + RS-8:** Student start / resume / revisit module quiz; Cognito required. Same visibility gate as QB-D `moduleQuiz` (published course + lesson access + published bank + `served_count_n` set); missing quiz/bank → **404** `not_found`. **403** `module_locked` when prior-module quiz gating blocks this module (RS-8). **Binding (QB-F):** first call draws **N** published questions without replacement and persists binding; while an attempt is **in_progress**, re-`start` keeps the same bound question **identities**; each post-submit new attempt with **`retake: true`** performs a **new random draw of N** from the current published bank and replaces the binding (§8.2–§8.4). **Attempt + shuffle (QB-G, migration **009** `module_quiz_attempts`):** one open **`in_progress`** attempt per binding; stable `shuffled_question_order` + per-question `shuffled_choice_orders`; re-`start` while that attempt is open returns the **same** `attemptId`, `questionIds`, and shuffled `questions` (§8.3–§8.4). **Optional body:** `{ "retake": true | false }` (default false). **`200`** includes **`phase`**: **`in_progress`** — `{ "moduleQuizId", "moduleId", "servedCountN", "attemptId", "attemptNumber", "questionIds", "questions": [{ "id", "promptText", "optionsJson" }] }`; student-safe payloads (never `correctOptionKey`, `questionBankId`, or bank `status` on this branch). **`latest_results`** — when the latest stored attempt is **submitted** and `retake` is false: top-level **`scorePercent`**, **`passPercent`**, **`passed`** plus **`latestSubmission`** (score totals + per-question breakdown including `correctOptionKey` / `selectedOptionKey` / `isCorrect`) **without** creating a new attempt (§11.3). **`retake: true`** after submit creates a **new** attempt, **redraws N** question identities from the published bank, and applies a fresh shuffle (§8.4, §11.4). **401** if unauthenticated. **409** `conflict` if published corpus < N at draw time, binding incomplete, shuffle validation fails, or fewer than N questions load from RDS. Student SPA: **Start quiz** → [`ModuleQuizPage.tsx`](frontend/src/pages/ModuleQuizPage.tsx) via [`StudentModuleQuizAuth.tsx`](frontend/src/components/auth/StudentModuleQuizAuth.tsx). Normative: [`plans/question-banks-requirements.md`](plans/question-banks-requirements.md) §7–§11.
POST   /courses/{id}/modules/{mid}/quiz/submit  // **QB-H + RS-8:** Explicit submit + scoring for the **`in_progress`** attempt. Same Cognito + visibility gate as start (**403** `module_locked` when gated). IDOR-safe **404** `not_found` when `attemptId` or path does not match the caller’s binding (**401**/`409`/`400` per [`plans/question-banks-requirements.md`](plans/question-banks-requirements.md) §10–§11 and locked error matrix in [`plans/question-banks-qb-h-plan.md`](plans/question-banks-qb-h-plan.md)). **Body:** `{ "attemptId", "answers": { "<questionId>": "<optionKey>", … } }` — keys must equal the bound question id set (**N** entries). **`200`:** `{ "attemptId", "attemptNumber", "correctCount", "totalCount", "scorePercent", "passPercent", "passed", "questions": [ { "id", "promptText", "selectedOptionKey", "correctOptionKey", "isCorrect" }, … ] }`. Graded row stored in **`module_quiz_attempt_submissions`** ([`010_module_quiz_attempt_submissions.sql`](infrastructure/database/migrations/010_module_quiz_attempt_submissions.sql)). API route wired in [`api-stack.yaml`](infrastructure/templates/api-stack.yaml) (**CatalogApiDeploymentV26**+; attempts route in same stack).
DELETE /courses/{id}/modules/{mid}      // Delete module and its lessons (CASCADE); cannot delete last module. Unknown {mid} is a 200 no-op (idempotent) — Cognito teacher/admin when enforced
```

### Lessons
```
GET    /courses/{id}/lessons             // Lesson rows: **moduleId**, **moduleOrder**, order (within module), title, videoStatus, optional thumbnailUrl; **no** videoKey — PUBLISHED public, DRAFT 404 unless owner/admin. Playback remains on GET /playback/...
POST   /courses/{id}/lessons            // Body: title; optional **moduleId** (defaults to first module by order). Presign flow via upload-url unchanged
PUT    /courses/{id}/lessons/{lid}      // Update lesson title
DELETE /courses/{id}/lessons/{lid}      // Delete lesson
PUT    /courses/{id}/lessons/{lid}/video-ready   // Mark uploaded video ready (MVP)
```

### Playback
```
GET  /playback/{courseId}/{lessonId}   // Provider playback contract; Kinescope `{ provider, videoId, drmAuthToken, watermarkText }` (name from given_name and/or family_name + email; 403 when email missing or both name claims blank), S3 `{ provider, playbackUrl }`; Cognito + enrollment (or owner/admin) when auth enforced. **RS-8:** **403** `module_locked` when the lesson’s module is quiz-gated locked for this student (prior module quiz not passed).
```

### Upload (Instructor)
```
POST /upload-url                       // Lesson video (courseId + lessonId + optional filesize) or
                                       // course thumbnail (courseId + uploadKind: "thumbnail", optional filename/contentType)
                                       // Returns provider upload contract: S3 presigned PUT URL or Kinescope POST endpoint + uploadMethod
```

### User profile (Auth)
```
GET   /users/me                        // Returns a per-user profile row (requires Cognito authorizer when enabled)
PATCH /users/me                        // Update profile fields (given/family name, country, profession, institution, researchInterests, termsAcceptedAt, privacyAcceptedAt); country/profession must match server allowlists
```

### Public contact (RS-10)
```
POST /contact                          // Public contact form (no JWT). Body JSON: name, email, category, subject, message; optional honeypot `rs_hp` (non-empty → **202** `{ "accepted": true }` without enqueue). Unknown keys → **400**. **202** `{ "accepted": true }` when accepted and enqueued. **503** when `TRANSACTIONAL_MAIL_QUEUE_URL` is unset or enqueue fails. **429** via RDS rate limits (`contact.ip`: 5 / 10 min per IP; `contact.global`: 30 / hour). Max body **16 KiB**. **No attachments.**
```

**Delivery:** Catalog Lambda (VPC, no NAT) validates and **`SendMessage`** to transactional-mail SQS ([`api-stack.yaml`](infrastructure/templates/api-stack.yaml) `TransactionalMailQueueUrl` → env **`TRANSACTIONAL_MAIL_QUEUE_URL`**). **Non-VPC** worker ([`transactional-mail-stack.yaml`](infrastructure/templates/transactional-mail-stack.yaml), [`infrastructure/lambda/transactional_mail/`](infrastructure/lambda/transactional_mail/)) consumes the queue and sends via **Zoho SMTP** (same Secrets Manager secret as Cognito CustomEmailSender — **not Amazon SES**). Contact jobs (`kind` omitted or `contact`) may only be delivered to **`support@researchspectrum.org`**. Grade notifications use `kind: notify` and one student address taken from RDS `users.email` (the HTTP client cannot set `to`).

### Lesson files and notes (RS-11)

```
GET    /courses/{id}/lessons/{lessonId}/files              // Cognito. Instructor: pending+ready metadata (no objectKey). Student: ready only after purchase + module unlock (RS-8).
POST   /courses/{id}/lessons/{lessonId}/files              // Instructor only. Body: title, kind (resource|download), fileType (pdf|csv|xlsx|docx|sav), byteSize (1..104857600). **201** { fileId, uploadUrl } — presigned PUT signs Content-Type + ContentLength.
PUT    /courses/{id}/lessons/{lessonId}/files/{fileId}/complete  // Instructor only. HEAD object; **400** on mismatch; marks ready.
GET    /courses/{id}/lessons/{lessonId}/files/{fileId}/url // Cognito + same access as list. **200** { url } presigned GET (300s); PDF resource inline, others attachment.
DELETE /courses/{id}/lessons/{lessonId}/files/{fileId}     // Instructor only; async S3 delete via media-cleanup queue when configured.

GET    /courses/{id}/lessons/{lessonId}/notes             // Author only. **200** { notes: [...] }
POST   /courses/{id}/lessons/{lessonId}/notes             // Body: body (1..4000, no tag-like markup), optional timestampSec (0..86400). Max 50 notes per user per lesson.
PATCH  /courses/{id}/lessons/{lessonId}/notes/{noteId}    // Author only.
DELETE /courses/{id}/lessons/{lessonId}/notes/{noteId}    // Author only.
```

**Storage:** Same private video bucket; keys `{courseId}/lessons/{lessonId}/files/{fileId}.{ext}`. Catalog IAM **`s3:GetObject`** includes `*/lessons/*/files/*` for presign + HEAD. Lesson/course delete enqueues file keys on the existing media-cleanup worker. Migration **019** (`lesson_files`, `lesson_notes`).

### Assignments (RS-13)

Cognito on every method except OPTIONS. Students need a purchase. An assignment belongs to one module and is **403** `module_locked` until every **earlier** module with a visible quiz is passed. The owning teacher or an admin bypasses that lock. Any number of assignments may set `countsTowardCertificate` (including none). This slice stores the flag and pass/fail. Issuance is [Certificates (RS-12)](#certificates-rs-12).

```
GET    /courses/{id}/assignments                         // { assignments: [...] }. Students: published only.
POST   /courses/{id}/assignments                         // Teacher. Body: title, moduleId, passPercent?, countsTowardCertificate?. **201** { assignment } draft.
GET    /courses/{id}/assignments/{assignmentId}          // { assignment }
PATCH  /courses/{id}/assignments/{assignmentId}          // Teacher. instructions/rubric/criteria/status.
DELETE /courses/{id}/assignments/{assignmentId}          // Teacher. Enqueues S3 keys, then deletes rows.

POST   /courses/{id}/assignments/{assignmentId}/images   // Teacher. slot instructions|rubric, contentType image/jpeg|png|webp|gif, byteSize 1..52428800. { uploadUrl }
POST   .../images/{slot}/complete                        // HEAD; marks the picture ready.
GET    .../images/{slot}/url                             // Presigned GET, inline, 300s.

POST   .../submissions                                   // Student opens a draft. **201**
GET    .../submissions                                   // { submissions }. Owner: all. Student: own rows only. No userId query.
GET    .../submissions/{submissionId}
POST   .../submissions/{submissionId}/files              // title, fileType pdf|csv|xlsx|docx|sav, byteSize 1..104857600. { fileId, uploadUrl }
POST   .../files/{fileId}/complete
GET    .../files/{fileId}/url                            // Attachment, sanitized filename, 300s.
POST   .../submissions/{submissionId}/submit             // Optional note. Requires one ready file.
POST   .../submissions/{submissionId}/grade              // Teacher. scores[{criterionId, points}], feedback. { scorePercent, passed }
```

**Rules:** Pass percent default **70** (instructor **1–100**). Score is integer half-up `(100 * awarded + maxTotal // 2) // maxTotal`. A passing grade closes further attempts. A failing grade allows a new draft. Grades are immutable. Instructions and the optional rubric narrative are plain text, sanitized rich text (`p`, `br`, `strong`, `em`, `ul`, `ol`, `li`, `https` links), or one picture. Scoring uses plain-text criterion labels and points (1–12 criteria). Caps: **20** assignments per course, **10** files per submission. Unknown JSON keys **400**.

**Storage:** `{courseId}/assignments/{assignmentId}/images/{slot}.{ext}` and `{courseId}/assignments/{assignmentId}/submissions/{submissionId}/{fileId}.{ext}`. Catalog **`s3:GetObject`** includes `*/assignments/*`. Course delete collects those keys before the row delete. Migration **020**. API stage deployment **CatalogApiDeploymentV43** (RS-12).

### Certificates (RS-12)

An entitled student receives **one** certificate per course when every **visible** module quiz is passed (published question bank, `served_count_n >= 1`, any attempt at that module’s pass mark) and every **published** assignment with `countsTowardCertificate` is passed. Lesson watch progress does not count. A course with no visible quiz and no published flagged assignment does not issue. Draft flagged assignments do not count. Entitlement is a paid course purchase at any course status, or a paid bundle of a **published** course. A bundle also covers an unpublished course when that student already has a quiz attempt or assignment submission on it, so unpublishing does not strand someone who already started. Untouched drafts are not listed. Teacher or admin ownership is not an entitlement. Unpublishing does not revoke a certificate already issued.

The row snapshots `givenName` + `familyName`, the course title, and the instructor line **Dr. Bahaa Aburayya** / **Founder & Instructor, Research Spectrum**. Later profile edits do not change it. A blank name blocks insert until both names exist. Revoke keeps the row (`revoked`) and does not mint a replacement.

Credential ID: `RS-{course 6 hex}-{UTC year}-{10 hex}` (example `RS-A1B7F3-2026-9C2E10B4D8`). `courses.certificate_code` is assigned at course create. Lookup is case-insensitive.

```
GET  /me/certificates                                      // Cognito. Issues when eligible, then { certificates, inProgress, profileIncomplete }. No email or userSub.
GET  /certificates/{credentialId}                          // Public. Valid/revoked: credentialId, status, studentName, courseTitle, issueDate (Month YYYY). Unknown: 404 { status: not_found } with no name. Malformed: 400, no DB read.
GET  /courses/{courseId}/certificates                      // Course owner or admin.
POST /courses/{courseId}/certificates/{certificateId}/revoke  // Owner or admin. Certificate must belong to the course.
```

Public verify is rate-limited: `certificate.verify.ip` 20 / 10 min per IP, `certificate.verify.global` 200 / hour. PDF download is client-side (`jspdf`, dynamic import on the student certificates page). There is no server PDF and no NAT path. Migration **021**. API deployment **CatalogApiDeploymentV43**. Prod apply of **021** is still pending (pre-launch).

### Research Team application (RS-14)

Eligible students apply to join the Research Team. **Required courses** are admin-flagged (`PUT /courses/{courseId}/research-team-requirement`); only **published** checked courses count. An empty required set means nobody can apply. Eligibility needs a **valid** (non-revoked) certificate for each required course and is enforced on **submit** only. Statuses: `submitted`, `under_review`, `accepted`, `rejected`. One open application (`submitted` or `under_review`) per student. Reapply only after admin **allow-reapply** on the latest rejected row; **accepted** is terminal for the student. Admin may move a rejected row to `under_review` or `accepted`. Review, status updates, allow-reapply, and the course checkbox require `custom:role=admin` (teacher role **403**). Application PII is stored in RDS and emailed to the applicant only (`kind: notify`, `bodyText` via the transactional-mail worker).

```
GET  /research-team/requirements                         // Public. { courses: [{ id, title }] } — published required courses.
GET  /me/research-team                                   // Cognito. Eligibility progress + latest application summary.
POST /me/research-team/applications                      // Cognito. Submit when eligible; one open application.
PUT  /courses/{courseId}/research-team-requirement       // Admin. Body: { required: boolean }.
GET  /research-team/applications                         // Admin. List applications.
GET  /research-team/applications/{id}                    // Admin. Application detail (includes form PII).
PATCH /research-team/applications/{id}                   // Admin. Status update.
POST /research-team/applications/{id}/allow-reapply      // Admin. Gate reapply after rejection.
```

Migration **022**. API deployment **CatalogApiDeploymentV44**. Prod apply of **022** / **V44** is still pending (pre-launch).

### Video provider webhooks
```
POST /webhooks/kinescope              // Provider status callback (`media.update.status`); optional
                                       // shared secret via ?token= or X-Kinescope-Webhook-Secret;
                                       // mutating events re-verified against Kinescope GET /videos/{id}
POST /webhooks/kinescope/drm-auth     // DRM auth callback; validates signed token + enrollment/access
```

---

## 8. React Frontend (MVP)

**User-visible brand:** **Research Spectrum** (strings, titles/meta, logo/favicons via [`frontend/src/lib/brand.ts`](frontend/src/lib/brand.ts) and shared header/footer). Repo, stacks, and infra names remain **StreamMyCourse**. Shared visual foundation (Tailwind `rs-*` tokens, self-hosted Plus Jakarta Sans, UI primitives) is in place. Public marketing routes (`/`, `/about`, `/faq`, `/contact`, `/research-team`), student app flows (catalog, detail, player, quiz, login, account), and instructor app pages (dashboard, course management, question banks, payment setup, assignment create/review) use that system. Student assignment page: `/courses/:courseId/assignments/:assignmentId`. Teacher: `/courses/:courseId/assignments` and `.../review`. Student certificates: `/certificates` (client PDF download). Public verification: `/verify/:credentialId`. Research Team apply: `/research-team/apply`; admin review: `/research-team/applications`. Legacy student paths (`/learn`, unrouted Figma pages) may still use older styling until cleaned up.

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
    │   ├── layout/                  # SiteHeader, ProfileMenu, Footer, Layout (optional `chromeHeader` for fixed app nav)
    │   ├── ui/                      # Shared RS primitives (Button, Card, Eyebrow, Kicker, SectionHeader, Badge, Field, Reveal)
    │   └── course/                  # CourseCard, CourseGrid, skeletons, thumbnail editor
    ├── lib/
    │   ├── api.ts                   # API client (fetch + env base URL); typed error helpers
    │   ├── brand.ts                 # User-visible Research Spectrum strings
    │   ├── page-title.ts            # `usePageTitle` → `Page — Research Spectrum`
    │   └── lessonGrouping.ts        # Group lessons by module; orphan moduleIds → Unsorted (student UI)
    └── pages/
        ├── HomePage.tsx             # Student landing (`/`)
        ├── CoursesCatalogPage.tsx   # Published course catalog (`/courses`)
        ├── CourseDetailPage.tsx
        ├── LessonPlayerPage.tsx
        ├── InstructorDashboard.tsx  # Teacher dashboard
        └── CourseManagement.tsx     # Course editing, modules, lessons, and upload
```

### Subdomain-Based Site Separation
The frontend is built as **two separate SPAs** deployed to different subdomains:

| Site | Domain | Purpose | Routes |
|------|--------|---------|--------|
| **Student** | `streammycourse.com` | Browse and watch courses | `/`, `/about`, `/faq`, `/contact`, `/research-team`, `/research-team/apply`, `/courses`, `/dashboard`, `/login`, `/privacy`, `/terms`, `/refund`, `/delivery`, `/educational-disclaimer`, `/courses/:id`, `/courses/:id/lessons/:id`, `/courses/:id/modules/:moduleId/quiz` (legacy `/details`, `/course`, `/catalog` redirect to `/courses`; **`/my-course`** → **`/dashboard`**) |
| **Teacher** | `teach.streammycourse.com` | Create, edit, upload content | `/`, `/courses/:id`, `/courses/:id/question-banks`, `/courses/:id/question-banks/:bankId`, `/settings/payments`, `/research-team/applications` (admin) |

### Student Site Routes (View-Only)
```
/                                    # Research Spectrum marketing home (catalog cards from public GET /courses; no prices)
/about                               # About instructor (public)
/faq                                 # FAQ (public)
/contact                             # Contact form → public POST /contact (RS-10)
/research-team                       # Research Team info + eligibility (lists admin-required published courses)
/research-team/apply                 # Signed-in application form (RS-14; eligibility enforced on submit)
/details                             # Legacy path → redirects to `/courses` (same as `/course`, `/catalog`)
/my-course                           # Legacy enrolled hub → redirects to `/dashboard`
/courses                             # Published course catalog (public `GET /courses`)
/dashboard                           # Signed-in learning hub (purchases + progress/quizzes; RS-9; Research Team block RS-14)
/login                               # Student sign-in (Hosted UI / auth shell)
/courses/:courseId                   # Course detail
/courses/:courseId/lessons/:lessonId # Video player
/courses/:courseId/modules/:moduleId/quiz # Module quiz (signed-in when Cognito enforced)
```

**Design vs backend gaps (student UI):** Tracked in **[`reports/figma-student-ui-gap-report.md`](reports/figma-student-ui-gap-report.md)** (e.g. catalog pacing, instructor display, pricing plans where the API remains MVP-free).

### Teacher Site Routes
```
/                                    # Instructor dashboard (create/list courses)
/courses/:courseId                   # Course management (edit, modules, lessons, upload, publish)
/courses/:courseId/question-banks    # Question bank list + create
/courses/:courseId/question-banks/:bankId # Question bank studio (draft/publish)
/settings/payments                   # PayTabs merchant setup + bundle USD price (billing teacher)
/research-team/applications          # Admin-only Research Team application review (RS-14)
/research-team/applications/:id      # Admin-only application detail + status / allow-reapply
```

### Build Configuration
- `vite.student.config.ts` → Build: `npm run build:student` → Output: `dist/student/`
- `vite.teacher.config.ts` → Build: `npm run build:teacher` → Output: `dist/teacher/`
- `npm run build:all` → Builds both sites

**Local dev:** set `VITE_API_BASE_URL` (see `frontend/.env.example` — copy to `frontend/.env`). Typical pattern: `VITE_API_BASE_URL=/api` with Vite proxy **`VITE_API_PROXY_TARGET`** pointing at the **prod** API Gateway root (required for `npm run dev` / `dev:student` / `dev:teacher` when using `/api`; default **`npm run dev`** uses [`vite.student.config.ts`](frontend/vite.student.config.ts)). Cognito Hosted UI env (`VITE_COGNITO_*`, `VITE_COGNITO_DOMAIN`) likewise targets **prod** pool outputs. There is **no** separate deployed dev API — local UI exercises prod backend + auth. Production SPAs rely on API CORS configuration. Vite `server.host: true` exposes a **Network** URL so phones on the same LAN use `http://<PC-LAN-IP>:<port>` (not `127.0.0.1` on the phone).

**Hosted UI / OAuth (local):** Amplify uses **`origin + '/'`** as the Cognito **`redirect_uri`**. **`streammycourse-student-*`** vs **`streammycourse-teacher-*`** app clients must list that exact URL (trailing slash) under **Hosted UI → Allowed callback URLs / sign-out URLs** — **`localhost` and `127.0.0.1` differ** (`auth-stack.yaml` defaults include both **5173** / **5174**); **`[::1]`** is normalized once to **`127.0.0.1`** in [`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts). GitHub **`STUDENT_COGNITO_*` / `TEACHER_COGNITO_*`** can override URLs; **`redirect_mismatch`** troubleshooting: [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md).

---

## 9. Security (MVP)

### API Safety (No Looping)
- Catalog Lambda is invoked **only** by API Gateway (no S3 events, no inbound SQS, no schedules). It may **enqueue** outbound jobs (e.g. transactional mail, billing fulfillment) to SQS; separate workers handle those queues.
- This prevents infinite chains/loops in the MVP.

### VPC / no-NAT invariant (catalog)
- The **in-VPC** catalog Lambda must **not** call the public internet (PayTabs, Google, **Zoho SMTP**, SES, etc.). Outbound email and other edge integrations use **SQS + a non-VPC worker** (same pattern as [`media-cleanup-stack.yaml`](infrastructure/templates/media-cleanup-stack.yaml) and [`video-provider-edge-stack.yaml`](infrastructure/templates/video-provider-edge-stack.yaml)). RDS VPC endpoints cover Secrets Manager, logs, SQS, S3, DynamoDB as needed for enqueue paths.

### Basic Protections
- S3 bucket: Private with presigned URL access (PUT for upload, GET for playback)
- Lambda IAM: `s3:PutObject` and `s3:GetObject` on `${bucket}/*` (upload + presigned playback; object keys are course/lesson-scoped under the same bucket); **RDS** path uses VPC + Secrets Manager + relational access; legacy DynamoDB policy applies only if the stack still attaches catalog table permissions for rollback
- CORS: Origin validation with configurable allowlist (`ALLOWED_ORIGINS`, set from CloudFormation `CorsAllowOrigin`); no implicit wildcard (empty env means misconfiguration). Use `ALLOWED_ORIGINS=*` only when intentionally allowing any origin in dev/tools. API Gateway GatewayResponses add CORS headers on 4XX/5XX
- Presigned uploads: allowed **video / image** `Content-Type` only for lesson video and thumbnails; **RS-11** lesson attachments use **pdf / csv / xlsx / docx / sav** under `{courseId}/lessons/{lessonId}/files/{fileId}.{ext}` with presigned PUT **Content-Length** signed to the declared byte size (max **100 MiB** per file). **RS-13** submission files use the same types and size under `{courseId}/assignments/{assignmentId}/submissions/{submissionId}/{fileId}.{ext}`; instruction pictures are jpeg/png/webp/gif up to **50 MiB** under `{courseId}/assignments/{assignmentId}/images/{slot}.{ext}`. S3 keys for video/thumbnails remain `{courseId}/lessons/{lessonId}/video/{uuid}.{ext}`, `{courseId}/lessons/{lessonId}/thumbnail/{uuid}.{ext}`, and `{courseId}/thumbnail/{uuid}.{ext}`; presigned playback **GET** for video/thumbnail keys only on the video adapter; lesson file **GET** uses a separate presign path. Conditional **repo** update when persisting a new **`videoKey`** after presign (mitigates concurrent upload races). S3 caps a single PUT at **5 GiB** (lesson files stay within the 100 MiB product limit).
- **Layered API abuse protection** (RDS route limits + API Gateway stage throttles); see [ADR-0012](plans/architecture/adr-0012-api-abuse-protection.md). **Product policy** (per-route RDS counters, 429 + `Retry-After`) vs **volumetric abuse** (stage throttles). RDS store errors **fail closed** with **503** (`rate_limit_store_unavailable`). **`GatewayResponseAllowOrigin`** is parameterized (default tightened away from `*` for dev/local)
- Video stack S3: **Block Public Access**, **SSE-S3** encryption, CORS allowlist parameter (no wildcard origin); **`Range`** / **`If-Range`** allowed for cross-origin HTML5 `<video>` playback
- **Stateful resource retention (CFN):** Templates set **`DeletionPolicy: Retain`** (and `UpdateReplacePolicy: Retain` where replacement is possible) on **`VideoBucket`** ([`video-stack.yaml`](infrastructure/templates/video-stack.yaml)), **`SiteBucket` / `TeacherSiteBucket`** ([`edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml)), **`MediaCleanupQueue` / `MediaCleanupDlq`** ([`media-cleanup-stack.yaml`](infrastructure/templates/media-cleanup-stack.yaml)), and **`BillingAlertTopic`** ([`billing-alarm.yaml`](infrastructure/templates/billing-alarm.yaml)); RDS uses `Snapshot` ([`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml)). New stateful resources (`AWS::S3::Bucket`, `AWS::DynamoDB::Table`, `AWS::RDS::DBInstance`, `AWS::SQS::Queue`, `AWS::SNS::Topic`) MUST be added with the same convention unless they hold provably ephemeral state.
- **Legacy** DynamoDB catalog tables (if orphaned from previous deployments): manually delete after confirming RDS migration is stable.
- Lambda JSON responses: **`X-Content-Type-Options`**, **`X-Frame-Options`**, **`Content-Security-Policy`** (API-oriented restrictive policy), **`Cache-Control: no-store`** on errors; **HSTS** when the response includes an **HTTPS** `Access-Control-Allow-Origin`
- Edge-hosted SPAs ([`edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml)): CloudFront **response headers policy** (HSTS, nosniff, frame deny, referrer policy) on default behaviors
- **Auth enforced:** Protected routes (mutations, `/courses/mine`, **`GET /playback/...`**, etc.) require a valid Cognito context and the controller rejects missing `sub`. Public reads remain public, but are wired to a **permissive API Gateway REQUEST authorizer** so authenticated callers can supply `sub`/`role` context **without any Cognito/JWKS calls** from the in-VPC catalog Lambda. Draft content still stays hidden (404) from non-managers and the API never returns `videoKey`. Thumbnail presigned URLs in those responses are effectively **public** for **PUBLISHED** courses — do not put PII or paid-only content in cover/lesson thumbnail images.
- **Student sign-in (RS-6):** **`streammycourse-student-*`** app client supports **Google OAuth** (Hosted UI redirect) and **native email/password** (`COGNITO` + `ALLOW_USER_SRP_AUTH`); verification and password-reset email via **Cognito CustomEmailSender** → **Zoho SMTP** when PreSignUp + custom sender Lambda + **`ZohoSmtpSecretArn`** deploy ([`auth-stack.yaml`](infrastructure/templates/auth-stack.yaml), secret **`streammycourse/zoho-smtp/prod`**). **PreSignUp** Lambda links Google sign-in to an existing native user with the same email and blocks duplicate native sign-up when the email already exists. Student SPA **terms gate:** protected routes require **`termsAcceptedAt`** and **`privacyAcceptedAt`** on the profile (legal pages exempt).
- **Teacher sign-in:** **`streammycourse-teacher-*`** remains **Google-only** (no native password on the public teacher client).
- **API Gateway vs Lambda:** The stage must point at a **deployment** that includes those authorizer settings. If the stage lags the REST API definition (CloudFormation updated methods but not the deployment snapshot), the browser can send a valid `Authorization` bearer while Lambda still sees **no** `requestContext.authorizer.claims` and returns **`Authentication required`** (`code: unauthorized`). The API stack ties **`AWS::ApiGateway::Deployment`** `Description` to **`LambdaCodeS3Key`** so each catalog zip upload publishes a new deployment; if drift is suspected, operators can run **`aws apigateway create-deployment`** for the REST API id and stage (see [`ImplementationHistory.md`](./ImplementationHistory.md)).
- Kinescope DRM auth callback is enforced through signed JWT claims (`KINESCOPE_DRM_JWT_SECRET`, issuer, audience) and existing lesson-access checks (`authorize_kinescope_drm` in service). Recording prevention capability is provider-managed, not a browser-only control.
- No sensitive data in logs (console logs removed from frontend)
- **Public legal pages (student SPA):** [`/privacy`](frontend/src/pages/legal/PrivacyPage.tsx), [`/terms`](frontend/src/pages/legal/TermsPage.tsx), [`/refund`](frontend/src/pages/legal/RefundPage.tsx), [`/delivery`](frontend/src/pages/legal/DeliveryPage.tsx), and [`/educational-disclaimer`](frontend/src/pages/legal/EducationalDisclaimerPage.tsx) are **unauthenticated** static routes (no Amplify bootstrap on first paint). Copy is **English-only**, centralized in [`legalConfig.ts`](frontend/src/lib/legalConfig.ts) (Research Spectrum entity, Jordan governing law, **`support@researchspectrum.org`**). Teacher SPA footer links to the **student origin** via [`legalUrls.ts`](frontend/src/lib/legalUrls.ts) and [`legal/links.ts`](frontend/src/lib/legal/links.ts) (`VITE_STUDENT_SITE_URL` override in dev). PayTabs merchant setup ([`TeacherPaymentSetup.tsx`](frontend/src/pages/TeacherPaymentSetup.tsx)) exposes terms/privacy absolute URLs for profile fields.

### Student single-session (MVP)

**Policy (implemented in repo; requires auth stack + catalog deploy + migration 013 apply):** at most **one active student session** per Cognito user. The **teacher app client is exempt** — same user may hold a concurrent teacher SPA session without cross-client sign-out.

| Layer | Behavior |
| --- | --- |
| **RDS authority** | [`users.student_active_session_id`](infrastructure/database/migrations/013_student_active_session.sql) — canonical session id; **soft rollout:** empty/`''` until the user's first student-client authentication (legacy tokens pass through). |
| **Cognito Pre Token Generation** | [`cognito_user_profile_sync/session_sync.py`](infrastructure/lambda/cognito_user_profile_sync/session_sync.py) on student `callerContext.clientId` only: **authentication** bumps session + injects ID claim `student_session_id`; **refresh** compares `request.clientMetadata.student_session_id` (presented) to RDS active session and **denies** stale refresh via unhandled Lambda error (no new tokens). Wired in [`auth-stack.yaml`](infrastructure/templates/auth-stack.yaml) (`PreTokenGeneration` + `custom:student_active_session_id`). Mechanism: [`plans/student-single-session-refresh-spike.md`](plans/student-single-session-refresh-spike.md). |
| **Catalog API guard** | [`services/auth/session.py`](infrastructure/lambda/catalog/services/auth/session.py) middleware in [`index.py`](infrastructure/lambda/catalog/index.py): student JWT `aud` + `student_session_id` claim vs RDS → **`401`** with **`code: session_superseded`**. |
| **Student SPA** | [`StudentSessionGuard`](frontend/src/student-app/StudentSessionGuard.tsx) registers refresh [`ClientMetadata`](frontend/src/lib/student-session-refresh.ts) and signs out on `session_superseded`; mounted in [`student-app/App.tsx`](frontend/src/student-app/App.tsx). |

**Client contract:** superseded devices receive **`session_superseded`** on protected API calls and failed refresh; user must sign in again. **`AdminUserGlobalSignOut` is not used** — it would revoke refresh tokens for both student and teacher clients on the shared pool.

---

## 10. Deployment (MVP)

**Environment model:** One **deployed AWS environment** — **`prod`** (`StreamMyCourse-*-prod` stacks, GitHub Environment **`prod`**). **Local** development uses Vite on `localhost:5173` / `5174` with proxy to **prod** API and Cognito (see §8). There is no dev/prod mirror in CI/CD or deploy scripts.

### Frontend (Static Hosting)

Two separate SPAs are hosted on AWS using S3 + CloudFront + Route 53:
- **Student site:** `researchspectrum.org` — browse and watch courses
- **Teacher site:** `teach.researchspectrum.org` — create and manage courses

**Architecture:** Private S3 bucket (Origin Access Control) → CloudFront CDN → Route 53 alias (per site)

**One-time setup (prod):**
```powershell
# 1. Register domain via Route 53 console (manual, captures DomainName and HostedZoneId)

# 2. Deploy unified edge-hosting stack (ACM + student + teacher hosting) in us-east-1
#    CloudFront ACM requirement: certificate must be in us-east-1.
cd infrastructure
.\deploy.ps1 -Template edge-hosting -StackName StreamMyCourse-EdgeHosting-prod `
    -Environment prod `
    -HostedZoneId Z123456789 `
    -DomainName researchspectrum.org `
    -TeacherDomainName teach.researchspectrum.org `
    -CertPrimaryDomain researchspectrum.org `
    -AttachCloudFrontAliases true
```

**CI/CD deployment (every push to `main`):**
- **Unified Deploy:** [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — after CI: **`deploy-edge-prod`** ([`scripts/deploy-edge.sh`](scripts/deploy-edge.sh)), **`deploy-rds-prod`** + **`apply-schema-prod`**, **`deploy-backend-prod`** (Cognito + [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) **prod**), **`integration-http-tests`** (HTTPS pytest against prod outputs), **`verify-prod-rds`**, then **student/teacher web** deploys — exact ordering and parallelism follow each job’s **`needs`** in the workflow file. Reusable SPA workflows read bucket and distribution IDs from the edge stack outputs. GitHub Environment **`prod`** variables **`ROUTE53_HOSTED_ZONE_ID`**, **`STUDENT_WEB_DOMAIN`**, **`TEACHER_WEB_DOMAIN`**, optional **`WEB_CERT_DOMAIN`** / **`WEB_CERT_SANS`**, and **`COGNITO_DOMAIN_PREFIX`** (required for full deploy) are documented in [`infrastructure/README.md`](infrastructure/README.md).
- **Lambda zip:** `catalog-prod-{gitSha12}.zip` so CloudFormation updates the function each commit.
- **OIDC:** `AWS_DEPLOY_ROLE_ARN`; bootstrap the role with [`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) via [`scripts/deploy-github-iam-stack.sh`](scripts/deploy-github-iam-stack.sh) / [`.ps1`](scripts/deploy-github-iam-stack.ps1) (**not** in CI/CD). The template creates an **`AWS::IAM::OIDCProvider`** when the account has no GitHub issuer yet; if `https://token.actions.githubusercontent.com` already exists, pass **`ExistingGithubOidcProviderArn`** (IAM allows one provider per that URL per account—deleting the CloudFormation stack does not remove a pre-existing provider). Policy statements mirror [`infrastructure/iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json) + [`iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) (backend policy includes **ACM us-east-1**, **Route 53**, **CloudFront** for edge stacks; **CloudFormation / Lambda / DynamoDB (if used) / RDS / logs** scoped to **`StreamMyCourse-*`** where feasible—S3 stays account-scoped for artifacts and generated video bucket names). SPA reusable workflows ([`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml), [`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml)) declare **`workflow_call` secrets**; [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) passes them explicitly (no blanket **`secrets: inherit`** on those calls). After changing IAM JSON or the template, sync the live role: [`scripts/apply-github-deploy-role-policies`](scripts/apply-github-deploy-role-policies.sh) or redeploy the IAM stack. Details: [`infrastructure/README.md`](infrastructure/README.md).
- **Concurrency:** `cancel-in-progress: false` on deploy workflows so overlapping pushes **queue** (no mid-deploy cancellation)
- **Prod pause / restore (operator):** [`scripts/teardown-prod.sh`](scripts/teardown-prod.sh), [`scripts/restore-prod.sh`](scripts/restore-prod.sh), [`scripts/export-pause-manifest.sh`](scripts/export-pause-manifest.sh), and [`infrastructure/docs/prod-shutdown-restore-runbook.md`](infrastructure/docs/prod-shutdown-restore-runbook.md) — retain S3 buckets + RDS snapshot, tear down stacks, restore from manifest. Local RDS deploy honors **`RESTORE_DB_SNAPSHOT_IDENTIFIER`** ([`scripts/deploy-rds-stack.sh`](scripts/deploy-rds-stack.sh)).
- **SPA build guard:** [`scripts/check-cognito-spa-env.mjs`](scripts/check-cognito-spa-env.mjs) fails builds when **`VITE_API_BASE_URL`** ends with **`/v1`** (API Gateway stage root must match CloudFormation **`ApiEndpoint`**, e.g. `.../prod` not `.../prod/v1`).

**SPA HTML entrypoints (important):**
- **Student** build uses `frontend/student.html` → `frontend/src/student-main.tsx`; build renames output to **`dist/student/index.html`** for CloudFront `DefaultRootObject`.
- **Teacher** build uses `frontend/teacher.html` → `frontend/src/teacher-main.tsx`; build renames output to **`dist/teacher/index.html`** (same pattern as student).

**Cache strategy:**
- `assets/*` (hashed files): `max-age=31536000,immutable` (1 year)
- `index.html`: `no-cache` (always fresh)
- Other root files: `max-age=3600` (1 hour)

**CORS configuration:** When adding hosted origins, update the API stack (and video bucket S3 CORS via **`CorsAllowedOrigins`** on **`StreamMyCourse-Video-prod`** — wired in [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) and [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1)) to include both student and teacher domains:

Prod API (`deploy-backend.sh`):

```powershell
.\deploy.ps1 -Template api -StackName StreamMyCourse-Api-prod -Environment prod `
    -CorsAllowOrigin "https://researchspectrum.org,https://teach.researchspectrum.org,http://localhost:5173,http://localhost:5174" `
    -GatewayResponseAllowOrigin "https://researchspectrum.org"
```

### Backend
- Deploy API Gateway + Lambda via CloudFormation ([`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml)); requires **RDS stack** (`RdsStackName` parameter). DynamoDB path was removed; the api stack now depends exclusively on RDS PostgreSQL.
- Lambda code packaged as a zip and uploaded to an artifacts S3 bucket; stack references `LambdaCodeS3Bucket` / `LambdaCodeS3Key`. **CI and [`deploy.ps1`](infrastructure/deploy.ps1)** use a **git-SHA-based key** (`catalog-prod-{sha}.zip`) so each deploy changes the parameter and the stack updates Lambda (fixed keys caused empty changesets).
- **Video provider env contract:** api stack passes `VIDEO_PROVIDER` (`kinescope`/`s3`/`vdocipher`) plus Kinescope vars `KINESCOPE_API_TOKEN`, `KINESCOPE_PARENT_ID`, `KINESCOPE_DRM_JWT_SECRET`, `KINESCOPE_DRM_JWT_ISSUER`, and `KINESCOPE_DRM_JWT_AUDIENCE`; `config.py` defaults to `VIDEO_PROVIDER=kinescope`. When **`VideoProviderEdgeLambdaArn`** is set with `VIDEO_PROVIDER=kinescope`, catalog **does not** receive upload/webhook Kinescope tokens (`KINESCOPE_API_TOKEN`, `KINESCOPE_PARENT_ID`, `KINESCOPE_WEBHOOK_SECRET` are empty on the VPC function); **`KINESCOPE_DRM_JWT_*`** stays on catalog for playback and `POST /webhooks/kinescope/drm-auth`.
- **Video provider edge (Kinescope, no NAT):** [`infrastructure/templates/video-provider-edge-stack.yaml`](infrastructure/templates/video-provider-edge-stack.yaml) deploys **`StreamMyCourse-VideoProviderEdge-prod`** — a **no-VPC** Lambda ([`infrastructure/lambda/video_provider_edge/`](infrastructure/lambda/video_provider_edge/)) for outbound Kinescope HTTP. [`scripts/deploy-video-provider-edge.sh`](scripts/deploy-video-provider-edge.sh) packages and deploys the edge stack; [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) runs it when `VIDEO_PROVIDER=kinescope`.
- **Course modules:** **`DELETE …/courses/{id}/modules/{moduleId}`** with lessons that reference **non-empty video/thumbnail keys** requires **`MEDIA_CLEANUP_QUEUE_URL`** on the catalog Lambda; if the queue URL is unset, the API returns **503** (same posture as **`DELETE …/lessons`** with media)—keep integration tests video-free unless the stack includes the media-cleanup deployment.
- **Auth stack (Cognito):** On each **prod** full deploy, [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) **requires** GitHub Environment variable **`COGNITO_DOMAIN_PREFIX`** and GitHub Environment secrets **`GOOGLE_OAUTH_CLIENT_ID`** + **`GOOGLE_OAUTH_CLIENT_SECRET`** (dedicated fail-fast steps), then packages [`infrastructure/lambda/cognito_user_profile_sync/`](infrastructure/lambda/cognito_user_profile_sync/) to S3 and runs `aws cloudformation deploy` for `StreamMyCourse-Auth-prod` with **Google OAuth parameters always**, **`RdsStackName`**, **`EnableUserProfileSync=true`**, and the sync Lambda S3 keys when RDS is in use.
- **SPA Cognito env (after auth stack exists):** Builds read **`VITE_COGNITO_*`**, **`VITE_API_BASE_URL`**, and **`VITE_COGNITO_DOMAIN`** from GitHub Environment **`prod`** secrets via [`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml) and [`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml).
- **Auth stack clients:** [`auth-stack.yaml`](infrastructure/templates/auth-stack.yaml) always provisions **Google** (`GoogleClientId` / `GoogleClientSecret` required). **Student** client: **`SupportedIdentityProviders: [COGNITO, Google]`** with **`ALLOW_USER_SRP_AUTH`** + OAuth code flow; Amplify **`loginWith.email`** + Hosted UI OAuth ([`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts)). **Teacher** client: **Google-only**. Register / verify / forgot-password pages on the student SPA; operator notes in [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md). Deploy packages **PreSignUp** Lambda zip on prod backend deploy.
- **Post-login SPA navigation:** Hosted UI returns to **`/`**; the app stores the pre-login in-SPA path in **`sessionStorage`** (sanitized in [`frontend/src/lib/post-login-return.ts`](frontend/src/lib/post-login-return.ts)) before **`signInWithRedirect`**, and [`frontend/src/components/auth/PostLoginRedirect.tsx`](frontend/src/components/auth/PostLoginRedirect.tsx) restores it after **`authStatus`** becomes **`authenticated`**. Each SPA entry ([`frontend/src/student-main.tsx`](frontend/src/student-main.tsx), [`frontend/src/teacher-main.tsx`](frontend/src/teacher-main.tsx)) mounts **`AuthenticatorProvider`** around **`BrowserRouter`** so auth hooks work on shell chrome ([`frontend/src/components/layout/Layout.tsx`](frontend/src/components/layout/Layout.tsx) **`chromeHeader`** → [`StudentHeader`](frontend/src/student-app/StudentHeader.tsx) / [`TeacherHeader`](frontend/src/teacher-app/TeacherHeader.tsx)) and **`/login`** ([`frontend/src/pages/StudentLoginPage.tsx`](frontend/src/pages/StudentLoginPage.tsx)).
- **Catalog Lambda:** no direct event sources in MVP (no S3 triggers on the catalog function, no schedules). **Async media cleanup:** [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) deploys **`StreamMyCourse-MediaCleanup-prod`** ([`infrastructure/templates/media-cleanup-stack.yaml`](infrastructure/templates/media-cleanup-stack.yaml) — SQS + DLQ + worker Lambda). **Transactional mail (RS-10):** [`scripts/deploy-transactional-mail.sh`](scripts/deploy-transactional-mail.sh) deploys **`StreamMyCourse-TransactionalMail-prod`** ([`infrastructure/templates/transactional-mail-stack.yaml`](infrastructure/templates/transactional-mail-stack.yaml)); [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) wires queue URL/ARN into the API stack unless overridden.
- **RDS PostgreSQL (deployed prod):** [`infrastructure/templates/rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) provisions a 1-AZ VPC, private **`db.t4g.micro`** (PostgreSQL 16, encrypted), Secrets Manager credential (auto-generated), and Interface / Gateway VPC endpoints.
- **RDS prod rollout via CI/CD:** [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) chains **`deploy-rds-prod`** → **`apply-schema-prod`** → **`deploy-backend-prod`** → **`integration-http-tests`** → **`verify-prod-rds`** ([`tests/integration/test_rds_path.py`](tests/integration/test_rds_path.py)).
- **Verify prod RDS auth:** **`verify-prod-rds`** calls [`.github/workflows/verify-rds-reusable.yml`](.github/workflows/verify-rds-reusable.yml) with **`github_environment: prod`**. GitHub Environment **`prod`** stores **`COGNITO_RDS_VERIFY_TEST_PASSWORD`**, optional **`COGNITO_RDS_VERIFY_JWT`**, optional **`COGNITO_RDS_VERIFY_TEST_USERNAME`**. Bootstrap user: [`scripts/ensure-ci-rds-verify-cognito-user.sh`](scripts/ensure-ci-rds-verify-cognito-user.sh); details: [`tests/integration/README.md`](tests/integration/README.md).
- Run: `cd infrastructure && .\deploy.ps1 -Template api -StackName StreamMyCourse-Api-prod -VideoBucketName <bucket>` (ensure `aws` is on PATH; full path `C:\Program Files\Amazon\AWSCLIV2\aws.exe` on Windows if needed)

### CI
- GitHub Actions ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): frontend `npm ci`, **ESLint** (`npm run lint`), **Knip** (`npm run knip`), **`npm run build:all`** (student + teacher production builds, including Cognito env contract), **`npm run test`** (Vitest SPA unit tests, including **jsdom** auth UI tests under `frontend/src/**/*.dom.test.tsx` such as [`SignIn.dom.test.tsx`](frontend/src/components/auth/SignIn.dom.test.tsx) — **`vitest.config.ts`** keeps **`coverage.enabled: false`** so CI does **not** instrument; optional local **`npm run test:coverage`** runs **`vitest run --coverage`** and writes summaries under **`frontend/coverage/`** (gitignored)); Lambda Python compile; **Vulture** (dead code); **Radon** `cc` (complexity, informational / `continue-on-error`); YAML parse for CloudFormation templates (including [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) for CI sanity on the IAM bootstrap template); **security scans** (`npm audit --audit-level=high`, **Checkov** for CloudFormation via [`.checkov.yaml`](.checkov.yaml), **pip-audit** across Python requirement files, and **Gitleaks** Git secret scan via [`.gitleaks.toml`](.gitleaks.toml)); **actionlint** on `.github/workflows`; **boundary import check** ([`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py)); Lambda **unit tests** including a **`bash -n`** guard on [`scripts/deploy-edge.sh`](scripts/deploy-edge.sh) and [`tests/unit/test_cognito_spa_env_contract.py`](tests/unit/test_cognito_spa_env_contract.py) for [`scripts/check-cognito-spa-env.mjs`](scripts/check-cognito-spa-env.mjs)

### Architecture notes (repo)
- Module map and ADRs: [`plans/architecture/`](plans/architecture/)
- Cursor rule for layers: [`.cursor/rules/clean-architecture-boundaries.mdc`](.cursor/rules/clean-architecture-boundaries.mdc)

### Environments

| Layer | Where | Notes |
|-------|--------|-------|
| **Local UI** | Vite (`http://localhost:5173` student, `5174` teacher) | [`frontend/.env.example`](frontend/.env.example): `VITE_API_BASE_URL=/api`, **`VITE_API_PROXY_TARGET`** → prod API Gateway; Cognito env from **`StreamMyCourse-Auth-prod`** outputs |
| **Deployed** | **`prod` only** | [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) on **`main`** (after [`ci.yml`](.github/workflows/ci.yml)): edge → RDS → backend → HTTPS integration pytest → verify RDS → SPAs; all jobs use GitHub Environment **`prod`** |
| **Integration tests** | Prod stacks | [`scripts/run-local-integration-tests.sh`](scripts/run-local-integration-tests.sh) / [`scripts/run-integration-tests.ps1`](scripts/run-integration-tests.ps1); requires **`INTEGRATION_ALLOW_PROD_CLEANUP=1`** for mutating tests ([`tests/integration/README.md`](tests/integration/README.md)) |
| **Legacy dev stacks** | Removed from repo | Operators tearing down old `*-dev` AWS resources: [`infrastructure/README.md`](infrastructure/README.md) **Phase 0** teardown; remove GitHub Environment **`dev`** after prod secrets verified |

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
| **Auth Provider** | Cognito (optional on API); **student** SPA: **Google + email/password**; **teacher** SPA: **Google only** | PreSignUp linking for same email; profile via **`PATCH /users/me`**; break-glass promotion via Console `custom:role` ([`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md)) |
| **Lambda Runtime** | Python | Better for media processing libraries |
| **Admin Tasks** | **RDS / SQL** (or legacy DynamoDB console only if on rollback path) | Direct data access for moderation; admin UI in Phase 3 |
| **Categories** | Flexible | Teacher/student role split is the key distinction; categories can be added dynamically |
| **Upload Limits** | 10GB per file | No time limit on video duration |
| **Local Testing** | Yes | Vite dev servers proxy to **prod** API/Cognito; integration pytest against prod via [`scripts/run-local-integration-tests.sh`](scripts/run-local-integration-tests.sh) |
| **Forgot Password** | Student native flows (RS-6) | Teacher remains Google-only |
| **Course Status** | Draft → Published | 2-state workflow (no pending review) |
| **DRM Provider** | None (MVP) | Deferred |

### User Roles
- **Hosted SPAs:** With Cognito configured (auth stack + SPA env), **students** sign in with **Google or email/password**; **teachers** with **Google** only. Operator promotion uses Console **`custom:role`**. Preview/catalog read policies remain as implemented in the API stack (some routes stay public by design).

---

## 13. Near-term backlog (after current MVP)

Ordered engineering priorities before large Phase 2 (monetization / DRM) work. Details and history: [`ImplementationHistory.md`](./ImplementationHistory.md); architecture decisions: [`plans/architecture/`](./plans/architecture/).

| Priority | Item | Goal |
|----------|------|------|
| 1 | **CloudFront (video)** | **Shipped:** CDN for MP4 via [`video-stack.yaml`](infrastructure/templates/video-stack.yaml); PriceClass_200; OAC + bucket policy so CloudFront can read the private video bucket; presigned **S3** playback remains primary; **`StreamMyCourse-CfInvalidate-<env>`** Lambda for `CreateInvalidation`. |
| 2 | **Frontend hosting** | **Shipped:** dual SPAs (student + teacher) to S3 + CloudFront + Route 53 via [`edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml) and the deploy pipeline (see §10). **Remaining:** ops polish (monitoring, cache tuning, domain/certificate hygiene). |
| 3 | **Auth** | **Shipped:** Cognito pool + required Google IdP; **student** client **Google + native email/password (SRP)** + **PreSignUp** linking + **Zoho CustomEmailSender**; **teacher** client Google-only; API authorizer + **`GET` / `PATCH /users/me`** (migration **016**); student register/verify/forgot flows + **terms gate**. **Ops:** **`GOOGLE_OAUTH_*`**, **`STUDENT_*` / `TEACHER_*` callback URLs**, GitHub **`ZOHO_SMTP_PASSWORD`** (Zoho app password for transactional mail), API **`CorsAllowOrigin`**. **Remaining:** tighten which routes are public vs Cognito-only (catalog still has open reads by design). |
| 4 | **RDS PostgreSQL (catalog)** | **Shipped and live in deployed prod:** [`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml), PostgreSQL adapters (`services/*/rds_repo.py`), migrator [`scripts/migrate-dynamodb-to-rds.py`](scripts/migrate-dynamodb-to-rds.py). **DynamoDB catalog fully removed** — api stack now requires `RdsStackName` and uses RDS exclusively. See [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md) and [`tests/integration/README.md`](tests/integration/README.md). **Question banks (repo + pipeline):** migrations **006**–**010** (bank name schema is folded into [`006_question_banks_module_quizzes.sql`](infrastructure/database/migrations/006_question_banks_module_quizzes.sql)); **QB-B** create bank + module quiz; stored publisher-editable bank names on create/list/rename; **QB-C/QB-E** draft question + publish ([`mcq_validation.py`](infrastructure/lambda/catalog/services/question_banks/mcq_validation.py)); **QB-D** optional `moduleQuiz` on `GET /courses/{id}/modules` ([`visibility.py`](infrastructure/lambda/catalog/services/question_banks/visibility.py)); **QB-F** binding draw + **QB-G** attempts + shuffle + **QB-H/I** submit, equal-weight grading ([`grading.py`](infrastructure/lambda/catalog/services/question_banks/grading.py)), discriminated **`POST .../quiz/start`** (`phase` `in_progress` \| `latest_results`, optional `retake`, `latestSubmission`), and **`POST .../quiz/submit`** ([`contracts.py`](infrastructure/lambda/catalog/services/question_banks/contracts.py), [`controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py)); student quiz UI [`ModuleQuizPage.tsx`](frontend/src/pages/ModuleQuizPage.tsx) + [`api.ts`](frontend/src/lib/api.ts). **RS-8 (repo):** migration **018** `pass_percent`, **`PATCH …/quiz`**, **`GET …/quiz/attempts`**, sequential module lock ([`gating.py`](infrastructure/lambda/catalog/services/question_banks/gating.py)), pass outcome fields on submit/start — child plan [`plans/ui-overhaul/rs-8-quiz-gating.md`](plans/ui-overhaul/rs-8-quiz-gating.md). **Prod:** migration **018** not applied pre-launch. API **CatalogApiDeploymentV27**+ in [`api-stack.yaml`](infrastructure/templates/api-stack.yaml). Unit: [`tests/unit/services/question_banks/`](tests/unit/services/question_banks/) (incl. submit, grading, gating, attempts). Integration: [`test_question_bank_start.py`](tests/integration/test_question_bank_start.py), [`test_question_bank_submit.py`](tests/integration/test_question_bank_submit.py) (authored for HTTPS post-deploy), permissions/publish/visibility, publisher reads. Normative: [`plans/question-banks-requirements.md`](plans/question-banks-requirements.md) §5–§11. **Remaining (repo backlog):** **QB-J** cross-stack audit ([`plans/question-banks-mega-plan.md`](plans/question-banks-mega-plan.md)). |
| 5 | **Security scanning in CI** | **Shipped baseline:** [`ci.yml`](.github/workflows/ci.yml) runs `npm audit --audit-level=high`, **Checkov** CloudFormation scanning with [`.checkov.yaml`](.checkov.yaml) baseline skips, **pip-audit** on Python requirements, and **Gitleaks** Git secret scanning via [`.gitleaks.toml`](.gitleaks.toml). RDS PostgreSQL now enforces TLS via `rds.force_ssl`. **Remaining:** burn down Checkov baseline skips as hardening items land. |
| 6 | **Billing / one-time purchases (RS-5)** | Shipped in repo — **USD** per-course price (`courses.price_amount_minor`) + platform **bundle** (`bundle_offers`); access via **`purchases`** (`paid` course or bundle grants all **published** courses for bundle buyers, including courses published later). **`POST /billing/checkout-session`** body `{ productType, courseId? }` → PayTabs HPP one-time sale (mock by default); IPN → SQS → fulfillment; refund IPN revokes by **`previous_tran_ref`**. Catalog: **`GET /billing/bundle`**, **`GET /billing/purchases`**, **`PATCH /billing/bundle`**, **`PATCH /billing/courses/{id}/price`**. Student **`/checkout`**, **`/account/purchases`**; **`purchase_required`** when no entitlement. Subscription routes/tables removed (**migration 015** drops `user_subscriptions` / `subscription_plans`). Ops: [`billing-ops-runbook.md`](infrastructure/docs/billing-ops-runbook.md). Pre-rollout: **`PAYTABS_USE_MOCK=true`**; live USD PayTabs profile is post-MVP ([WS9](plans/billing-workstream-9-paytabs-live-go-live.md) superseded in intent by RS-5 product model). |
| 7 | **Legal / merchant disclosure** | **Shipped (frontend):** English **Privacy**, **Terms**, **Refund**, **Delivery**, and **Educational Disclaimer** on student SPA ([`legalConfig.ts`](frontend/src/lib/legalConfig.ts), [`frontend/src/lib/legal/content/`](frontend/src/lib/legal/content/)); teacher footer + PayTabs setup use absolute student URLs via [`legalUrls.ts`](frontend/src/lib/legalUrls.ts). **Remaining:** counsel review of EN copy before PayTabs go-live. |

**Technical hygiene (ongoing):** extend typed `contracts` at the controller edge as endpoints grow. (Lambda artifact keys: **shipped** in CI/`deploy.ps1` — see §10.)

---

## 14. Post-MVP roadmap (Phase 2+)

See [`roadmap.md`](./roadmap.md) for phased vision (payments, scale, admin, search, live streaming, and additional video/provider evolution) and cost notes. §13 is the **bridge** between today’s baseline and that document’s Phase 2+ items.

---

*End of MVP Design Document*
