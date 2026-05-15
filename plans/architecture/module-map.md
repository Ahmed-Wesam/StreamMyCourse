# StreamMyCourse — Module map (Lambda package)

This document is the “public surface” map for the Python Lambda under `infrastructure/lambda/catalog/`.

## Composition / entry

| Module | Responsibility | Public API |
|--------|----------------|------------|
| `index.py` | Lambda entrypoint | `lambda_handler` |
| `bootstrap.py` | Dependency wiring (composition root) | `lambda_bootstrap()` → `(cfg, course_svc, auth_svc, progress_svc, question_bank_svc)` when RDS is complete; **QB-F:** `_StudentLessonAccessAdapter`, `_CourseReadAdapter` → `QuestionBankService` start ports |
| `config.py` | Environment configuration | `load_config()`; `pick_origin` helpers live in `services/common/http.py` |

## Bounded contexts

### `services/question_banks/` (QB-A domain, QB-B–E HTTP + authz + publish, QB-D visibility, QB-F binding + start, QB-G attempts + shuffle, QB-H/I submit + grading + start phases)

| File | Layer | Notes |
|------|-------|-------|
| `models.py` | Domain | `QuestionBank`, `ModuleQuiz`, `Question` (RDS-aligned); **QB-F:** `StudentModuleQuizBinding`; **QB-G:** `ModuleQuizAttempt`, `BoundQuestion` |
| `ports.py` | Contracts | `CourseMutateAuthorizerPort` (publisher writes); **QB-F:** `StudentLessonAccessPort`, `CourseReadPort` — start gate without importing `course_management` |
| `service.py` | Domain/application | `QuestionBankService` — authorizer before every repo write; publish §9.3 / N §5; draft + published-question rules; **QB-F + QB-G + QB-I:** `start_module_quiz` (QB-D gate + idempotent binding + resolve/create `in_progress` or return `latest_results` + `latestSubmission`; optional `retake` + fresh shuffle); **QB-H:** `submit_module_quiz` |
| `controller.py` | HTTP adapter | Publisher: `POST .../question-banks`, `.../questions`, `.../publish`, `POST .../modules/{mid}/quiz`. Student: **`POST .../modules/{mid}/quiz/submit`**, **`POST .../quiz/start`** ( **`quiz/submit` before `quiz/start` before bare `quiz`** ). Cognito claims → service |
| `contracts.py` | API DTOs | **QB-F/QB-G/QB-I:** discriminated **`StudentQuizStartInProgressDto` \| `StudentQuizStartLatestResultsDto`** + `StudentQuizStartBodyDto`; **QB-H:** `StudentQuizSubmitRequestDto`, `StudentQuizSubmitResponseDto`; `StudentQuizQuestionDto` (student-safe); result rows with `correctOptionKey` only in submit/`latestSubmission` payloads |
| `binding_draw.py` | Domain (pure) | **QB-F:** `draw_question_ids` — uniform sample without replacement |
| `presentation_shuffle.py` | Domain (pure) | **QB-G:** question-order and per-question choice-key shuffle + `apply_presentation_shuffle` (injectable `rng`) |
| `grading.py` | Domain (pure) | **QB-H:** equal-weight grading / answer validation helpers (no HTTP) |
| `visibility.py` | Domain (pure) | **QB-D:** `apply_module_quiz_visibility` — gates repo map by `course_status` + `has_lesson_access` |
| `rds_repo.py` | Persistence adapter | `question_banks`, `module_quizzes`, `questions`; transactional publish; **QB-D:** `list_module_quiz_visibility_for_course`; **QB-F:** `student_module_quiz_bindings` / `student_module_quiz_binding_questions`, `list_published_question_ids`, binding CRUD; **QB-G:** `module_quiz_attempts` (insert/load open attempt, `mark_attempt_submitted` for tests); **QB-H:** `module_quiz_attempt_submissions` (**010**): insert submission + mark submitted, latest submission for binding, attempt+binding fetches for submit authz; maps integrity errors to HTTP types |

**Cross-context rule:** `question_banks` must not import `course_management` or `auth` (same as other leaves).

### `services/course_management/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | Parses API Gateway events, maps errors to JSON, returns API responses; **`GET /courses/{id}`** / **`GET /courses/{id}/lessons`** are unauthenticated at the edge (**`AuthorizationType: NONE`**) and rely on **`service.list_lessons_public`** + **`get_course_detail_with_enrollment`** for DRAFT hiding |
| `service.py` | Domain/application | Business rules; depends on **ports** only; **QB-D:** `list_course_modules_public` merges optional `moduleQuiz` via `ModuleQuizVisibilityPort` |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | psycopg2-based `CourseCatalogRepositoryPort` implementation |
| `storage.py` | Infrastructure adapter | S3 presign generation |
| `ports.py` | Contracts | `Protocol` interfaces for repo/storage; **QB-D:** `ModuleQuizVisibilityPort` (implemented in `bootstrap.py`, not imported from `question_banks`) |
| `models.py` | Domain models | `Course`, **`CourseModule`**, `Lesson`, `PresignResult` (lesson carries `moduleId` + module display order from join) |
| `contracts.py` | API DTOs | TypedDicts for JSON shapes returned by controller |

**Cross-context rule:** `course_management` must not import `services.auth` (enforced in CI).

### `services/auth/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | `/users/me` handler |
| `service.py` | Domain/application | Depends on `UserProfileRepositoryPort` |
| `ports.py` | Contracts | `UserProfileRepositoryPort` Protocol |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | `UserProfileRdsRepository` |

**Cross-context rule:** `auth` must not import `course_management` (enforced in CI).

### `services/enrollment/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `ports.py` | Contracts | `EnrollmentRepositoryPort` |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | Idempotent upserts via `ON CONFLICT DO NOTHING` |

### `services/progress/` (implemented)

| File | Layer | Notes |
|------|-------|------|
| `controller.py` | HTTP adapter | `GET /courses/{id}/progress`, `PUT /courses/{id}/lessons/{id}/progress` |
| `service.py` | Domain/application | Authorization, auto-complete ratio, position validation |
| `rds_repo.py` | Persistence adapter (PostgreSQL) | psycopg2-based; ON CONFLICT UPDATE upserts |
| `ports.py` | Contracts | `LessonProgressRepositoryPort` |
| `contracts.py` | API DTOs | `CourseProgressResponse`, `LessonProgressItem` |

**Cross-context rule:** `progress` imports `enrollment` (for auth checks) but not `course_management` directly (uses repository port).

### `services/common/` (shared kernel)

Cross-cutting utilities shared by multiple contexts:

- `errors.py` — typed HTTP errors (`HttpError` hierarchy)
- `http.py` — CORS + JSON response helpers
- `validation.py` — strict JSON parsing + simple validators
- `sqs_client.py` — enqueue async media-cleanup jobs to SQS (boto3 SQS; used after course delete)

## What other modules may import

- Controllers may import `services/common/*` and their own `contracts.py`.
- Services may import `ports.py`, `models.py`, and `services/common/errors.py` (not HTTP helpers). They may call `sqs_client.send_media_cleanup_job` for the async delete path (no HTTP imports).
- Repos/storage may import `boto3` and Dynamo/S3 specifics.
- `rds_repo.py` modules may import `psycopg2`; no other module may (enforced in CI).
- `bootstrap.py` may import both `boto3` (Secrets Manager) and `psycopg2` (connection) -- it is the composition root.

## Enforcement

- Cursor rule: `.cursor/rules/clean-architecture-boundaries.mdc`
- CI script: `scripts/check_lambda_boundaries.py` (runs in GitHub Actions)
