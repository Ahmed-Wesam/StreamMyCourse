# StreamMyCourse — Implementation History

> Living document tracking all implementation progress, decisions, and milestones.

---

## 2026-05-18 — WS1 — Billing access policy + RDS schema (pre-release)

### Completed

- [x] **Migration** — [`011_billing_subscription.sql`](infrastructure/database/migrations/011_billing_subscription.sql): `subscription_plans`, `teacher_merchant_accounts`, `user_subscriptions`, `payment_webhook_events`.
- [x] **Policy doc** — [`access-policy-v1.md`](plans/billing/access-policy-v1.md): subscription-only, monthly JOD, Jordan, no `BILLING_ENABLED`.
- [x] **Deploy bundle** — migration `011` in [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml), [`scripts/deploy-rds-stack.sh`](scripts/deploy-rds-stack.sh), and [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1) dev+prod schema lists.
- [x] **Schema integrity** — `user_subscriptions` composite FK `(plan_id, environment)` → `subscription_plans (id, environment)`; seed `plan_key` `monthly_all_access`.
- [x] **Unit tests** — [`test_rds_schema_apply.py`](tests/unit/test_rds_schema_apply.py).
- **Pre-release** — zero users; WS5 enforces access before launch.
- **Out of scope this PR** — catalog gates (WS5), PayTabs (WS2+).

---

## 2026-05-17 — Draggable mobile curriculum bottom sheet

### Completed

- [x] **Snap math** — [`bottomSheetSnap.ts`](frontend/src/lib/bottomSheetSnap.ts): partial cap (88% viewport, max 720px), drag-relative dismiss/expand thresholds; unit tests in [`bottomSheetSnap.test.ts`](frontend/src/lib/bottomSheetSnap.test.ts).
- [x] **Component** — [`DraggableBottomSheet.tsx`](frontend/src/components/layout/DraggableBottomSheet.tsx): drag handle, partial/full snaps, keyboard (Arrow up/down, Escape), deferred height measure with safe listener cleanup; DOM tests in [`DraggableBottomSheet.dom.test.tsx`](frontend/src/components/layout/DraggableBottomSheet.dom.test.tsx).
- [x] **Lesson player** — [`LessonPlayerMobileView.tsx`](frontend/src/pages/lesson-player/LessonPlayerMobileView.tsx) replaces static overlay; [`LessonPlayerPage.dom.test.tsx`](frontend/src/pages/LessonPlayerPage.dom.test.tsx) asserts drag handle `role="slider"`.

---

## 2026-05-17 — Question bank duplicate MCQ option key guard

### Completed

- [x] **Validation** — [`mcq_validation.py`](infrastructure/lambda/catalog/services/question_banks/mcq_validation.py): `validate_mcq_options_json` rejects duplicate non-empty option keys (`400` `optionsJson must not contain duplicate option keys`); applies on create/update/publish paths via existing callers.
- [x] **Tests** — [`test_mcq_validation.py`](tests/unit/services/question_banks/test_mcq_validation.py), [`test_question_bank_service.py`](tests/unit/services/question_banks/test_question_bank_service.py).
- [x] **Studio UX** — [`apiUserMessages.ts`](frontend/src/lib/apiUserMessages.ts): maps duplicate-key errors to friendly copy (no raw `optionsJson` in UI); rule ordered before generic options-json message.

---

## 2026-05-17 — Student courses UI restyle and route consolidation

### Completed

- [x] **Routes** — [`App.tsx`](frontend/src/student-app/App.tsx): **`/courses`** → enrolled hub ([`MyCoursePage.tsx`](frontend/src/pages/MyCoursePage.tsx)); **`/details`** marketing page; legacy **`/catalog`**, **`/my-course`**, and **`/course`** redirect. Removed standalone [`CourseCatalogPage`](frontend/src/pages/CourseCatalogPage.tsx) and catalog card components.
- [x] **Header** — [`StudentHeader.tsx`](frontend/src/student-app/StudentHeader.tsx): Home / Details / Pricing / Courses nav aligned with new paths.
- [x] **Course detail** — [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx): Home-style hero, stats strip, flowing curriculum layout; error-safe hero title and hidden stats on load failure; [`PricingSection`](frontend/src/components/course/PricingSection.tsx) `band` variant.
- [x] **Lesson player** — [`quizScoreDisplay.ts`](frontend/src/lib/quizScoreDisplay.ts): colored score pill thresholds and singular/plural question count in module quiz sidebar row.
- [x] **Lesson player (mobile)** — [`LessonPlayerMobileView.tsx`](frontend/src/pages/lesson-player/LessonPlayerMobileView.tsx) below `md`; shared chrome in [`lessonPlayerUi.tsx`](frontend/src/pages/lesson-player/lessonPlayerUi.tsx); [`useMediaQuery.ts`](frontend/src/lib/useMediaQuery.ts) + `readMdUpMatch`; sticky lesson header under site nav; no nested scroll in lesson details; desktop sidebar hamburger only when collapsed; dismissed sidebar preserved across breakpoint changes.
- [x] **Lesson player (module quiz nav)** — [`resolveNextModuleQuizHref`](frontend/src/pages/lesson-player/lessonPlayerUi.tsx) / [`resolvePrevModuleQuizHref`](frontend/src/pages/lesson-player/lessonPlayerUi.tsx): **Next** after the last lesson in a module targets the current module quiz, then quiz-only modules before the next module with lessons; **Previous** from the first lesson in a module targets the prior module quiz (including quiz-only modules). Wired on desktop header, playback nav, and mobile footer; unit + DOM tests.
- [x] **Docs** — [`design.md`](design.md) student route table and frontend tree updated.

### Verify

- [ ] `cd frontend && npm ci && npm run lint && npm run test && npm run build:all`

---

## 2026-05-16 — Module quiz latest score on course modules list

### Completed

- [x] **`moduleQuiz.latestScorePercent`** — [`GET /courses/{id}/modules`](design.md): optional whole percent (half away from zero) when the viewer has a latest submitted attempt; batch-loaded in [`bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py) via [`list_latest_submission_scores_for_course`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py).
- [x] **Lesson player sidebar** — [`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx) shows the percent under the Quiz pill when present.
- [x] **Tests** — integration [`test_module_list_includes_latest_score_percent_after_submit`](tests/integration/test_question_bank_visibility.py); unit coverage for rounding, adapter merge, and RDS query.
- [x] **Review follow-up** — `deleteQuestionBankQuestion` error context in question bank studio; [`design.md`](design.md) QB-D contract updated.

---

## 2026-05-16 — Frontend API error sanitization and question bank UX

### Completed

- [x] **`catalogApiUserMessage`** — [`apiUserMessages.ts`](frontend/src/lib/apiUserMessages.ts): maps technical catalog API errors to plain-language copy; context-specific fallbacks; passive voice (no “we”); blocks field names and opaque status strings. Re-exported from [`questionBankErrors.ts`](frontend/src/lib/questionBankErrors.ts) for question-bank call sites.
- [x] **App-wide wiring** — course management, instructor dashboard, student catalog, lesson player, module quiz, learn redirect, and teacher role gate use the sanitizer instead of raw `err.message`.
- [x] **Question bank studio** — hide raw bank/module IDs in list and studio; friendly Draft/Published labels; linked-module panel; publish uses attached module (no module dropdown); required correct answer on add question.
- [x] **Quiz navigation** — [`moduleQuizNavigation.ts`](frontend/src/lib/moduleQuizNavigation.ts): “Back” from module quiz returns to lesson player when possible.
- [x] **Review follow-up** — no verbatim pass-through of unmapped API text; operation-specific contexts (quiz, question banks, attach module quiz); `LearnRedirectPage` and module quiz retake/submit guard state updates after unmount; quiz `returnTo` validated against loaded lessons; publish warning when multiple module links exist.
- [x] **Review follow-up (lifecycle + copy)** — `LearnRedirectPage` aborts after each await; `moduleQuizBackLabel` for back link text; studio/list `mountedRef` / `cancelled` guards; linked-module multi-link warning; DOM tests use matching error contexts.
- [x] **Studio reload generation** — `QuestionBankStudioPage` `loadGenerationRef` invalidates in-flight `reload()` when `bankId` changes or the page unmounts.

### Verify

```bash
cd frontend && npm run lint && npm run knip && npm run build:all && npm run test
```

---

## 2026-05-16 — Module quiz retake random redraw

### Completed

- [x] **Retake redraw** — [`service.py`](infrastructure/lambda/catalog/services/question_banks/service.py) `_retake_with_redraw` + [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py) `redraw_binding_and_insert_attempt`: `POST .../quiz/start` with `retake: true` after submit draws a fresh **N** from the current published bank, replaces binding, and shuffles presentation (§8.4).
- [x] **`latest_results` fix** — recap uses the submitted attempt’s question order / grading rows, not stale binding ids after a redraw ([`test_latest_results_uses_submission_question_order_not_binding`](tests/unit/services/question_banks/test_question_bank_attempts.py)).
- [x] **Submit set assert** — `submit_module_quiz` rejects when attempt shuffle ids ≠ current binding (`409` *does not match current question set*); covered in [`test_question_bank_submit.py`](tests/unit/services/question_banks/test_question_bank_submit.py).
- [x] **Docs + student copy** — [`plans/question-banks-requirements.md`](plans/question-banks-requirements.md) §8.2/§8.4/§9.5/§12/§13; [`design.md`](design.md) `quiz/start` binding bullet; [`ModuleQuizPage.tsx`](frontend/src/pages/ModuleQuizPage.tsx) retake helper text.

### Files touched (production slice, prior to this doc/copy pass)

- [`infrastructure/lambda/catalog/services/question_banks/service.py`](infrastructure/lambda/catalog/services/question_banks/service.py)
- [`infrastructure/lambda/catalog/services/question_banks/rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py)
- [`tests/unit/services/question_banks/test_question_bank_attempts.py`](tests/unit/services/question_banks/test_question_bank_attempts.py)
- [`tests/unit/services/question_banks/test_question_bank_submit.py`](tests/unit/services/question_banks/test_question_bank_submit.py)
- [`tests/integration/test_question_bank_submit.py`](tests/integration/test_question_bank_submit.py)

### Verify

```bash
python -m pytest tests/unit/services/question_banks/test_question_bank_attempts.py tests/unit/services/question_banks/test_question_bank_submit.py -q
cd frontend && npm run test -- ModuleQuizPage.dom.test.tsx -q
```

---

## 2026-05-16 — One module per question bank

### Completed

- [x] **Partial unique index** — [`006_question_banks_module_quizzes.sql`](infrastructure/database/migrations/006_question_banks_module_quizzes.sql): `uq_module_quizzes_course_question_bank`; applied on dev/prod via query-rds.
- [x] **Service + repo** — pre-check in [`service.py`](infrastructure/lambda/catalog/services/question_banks/service.py) and unique-constraint mapping in [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py) for **409** `conflict` when a bank is already linked to a different module.
- [x] **Teacher UI** — [`CourseManagementModuleQuizPanel`](frontend/src/components/course/CourseManagementModuleQuizPanel.tsx) filters the attach picker so banks already linked elsewhere in the course are not offered.
- [x] **Integration test** — [`tests/integration/test_question_bank_one_bank_per_module.py`](tests/integration/test_question_bank_one_bank_per_module.py).

---

## 2026-05-16 — CI security scanner baseline

### Completed

- [x] **Security CI gate** — [`.github/workflows/ci.yml`](.github/workflows/ci.yml) adds a **Security scans** job with `npm audit --audit-level=high`, **Checkov** CloudFormation scanning, **pip-audit** across Python requirement files, and **Gitleaks** Git secret scanning via [`.gitleaks.toml`](.gitleaks.toml).
- [x] **Checkov baseline** — [`.checkov.yaml`](.checkov.yaml) documents current MVP hardening skips so new unbaselined CloudFormation findings fail CI while known backlog items remain visible.
- [x] **RDS TLS enforcement** — [`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) sets `rds.force_ssl: '1'`; catalog Lambda already connects with `sslmode=require`, so the database now rejects accidental plaintext clients.
- [x] **Agent workflow updates** — [`.cursor/skills/security-scans/SKILL.md`](.cursor/skills/security-scans/SKILL.md), [`commit`](.cursor/skills/commit/SKILL.md), [`review-and-commit`](.cursor/skills/review-and-commit/SKILL.md), and [`watch-ci-after-push`](.cursor/skills/watch-ci-after-push/SKILL.md) now include the security scanner workflow.
- [x] **Dependency audit cleanup** — [`frontend/package-lock.json`](frontend/package-lock.json) refreshed by `npm audit fix` to remove the high-severity `fast-xml-builder` advisory pulled through Amplify storage.

### Verify

```bash
cd frontend && npm audit --audit-level=high
python -m checkov.main --config-file .checkov.yaml --skip-download
gitleaks git . --config .gitleaks.toml --redact --no-banner --verbose --log-opts=HEAD
```

`pip-audit` was not run locally because this Windows environment only exposes Python 3.14 and the repo/CI scanner uses Python 3.11 wheels for `psycopg2-binary`.

---

## 2026-05-16 — Question bank names contract and final verification

### Completed

- [x] **API contract docs** — [`design.md`](design.md) §7 now records named question-bank create/list/rename behavior: `POST /courses/{courseId}/question-banks` requires `{ "name": "..." }` and returns `{ "questionBankId", "name" }`; `GET /courses/{courseId}/question-banks` includes `name`; `PATCH /courses/{courseId}/question-banks/{questionBankId}` renames DRAFT or PUBLISHED banks and returns the same write shape.
- [x] **MVP baseline docs** — [`design.md`](design.md) §13 and [`roadmap.md`](roadmap.md) MVP baseline now mention stored publisher-editable names folded into [`006_question_banks_module_quizzes.sql`](infrastructure/database/migrations/006_question_banks_module_quizzes.sql), API **CatalogApiDeploymentV27**, and that student quiz routes remain bank-name-free.
- [x] **Behavioral decisions captured** — names are trimmed, non-empty, max 80 chars, not unique, and editable after publish; older rows keep UI/API fallback behavior where applicable.

### Verify

```bash
python -m pytest tests/unit/services/question_banks/ -q
python scripts/check_lambda_boundaries.py
cd frontend && npm run test -- src/lib/api.questionBanks.test.ts src/pages/QuestionBanksListPage.dom.test.tsx src/pages/QuestionBankStudioPage.dom.test.tsx src/pages/CourseManagement.dom.test.tsx
cd frontend && npm run lint
```

Integration tests requiring Cognito/dev-stack secrets were not run in this docs/final-verification slice.

---

## 2026-05-15 — Frontend Epic 5: smoke checklist notes and docs closure

### Completed

- [x] **Route hardening coverage** — [`frontend/src/pages/CourseManagement.dom.test.tsx`](frontend/src/pages/CourseManagement.dom.test.tsx) and [`frontend/src/teacher-app/App.dom.test.tsx`](frontend/src/teacher-app/App.dom.test.tsx) cover the teacher course-management route flows added in prior slices.
- [x] **Production nav unchanged** — no production navigation or API/product contract changes were needed for this hardening slice.
- [x] **Docs closure** — `design.md` and `roadmap.md` already describe the current MVP/product contract; no product-scope doc changes were required.

### Verify

Automated smoke/status from prior Epic 5 slices:

```bash
cd frontend && npm run test -- src/pages/CourseManagement.dom.test.tsx src/teacher-app/App.dom.test.tsx
cd frontend && npm ci && npm run lint && npm run knip && npm run build:all && npm run test
```

Focused route tests passed: **2 files / 40 tests**. Full frontend quality gate passed: **39 files / 336 tests**. Warnings were existing React peer/audit notices, Vite chunk-size/plugin timing warnings, and known Amplify/`scrollTo` test stderr noise. No live manual browser smoke was performed for this docs-only closure.

---

## 2026-05-15 — Frontend Epic 4: student module quiz UX and lesson-player entry

### Completed

- [x] **Catalog error copy** — [`frontend/src/lib/questionBankErrors.ts`](frontend/src/lib/questionBankErrors.ts): `catalogApiUserMessage`; `questionBankUserMessage` delegates so teacher + student share 404/409/fallback rules.
- [x] **Module quiz page** — [`frontend/src/pages/ModuleQuizPage.tsx`](frontend/src/pages/ModuleQuizPage.tsx): `catalogApiUserMessage` on start / retake / submit errors; copy for `in_progress` vs `latest_results`; retake explainer; submit-disabled helper + `aria-describedby`.
- [x] **Tests** — [`frontend/src/pages/ModuleQuizPage.dom.test.tsx`](frontend/src/pages/ModuleQuizPage.dom.test.tsx): ApiError branches, phase copy, submit helper when incomplete.
- [x] **Lesson player** — [`frontend/src/pages/LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx): module quiz as sidebar row when `moduleQuiz.available` and enrolled; **Next** targets module quiz after the last lesson in that module before the next lesson.
- [x] **Lesson player tests** — [`frontend/src/pages/LessonPlayerPage.dom.test.tsx`](frontend/src/pages/LessonPlayerPage.dom.test.tsx): quiz row + Next routing scenarios.

### Verify

```bash
cd frontend && npm run test -- ModuleQuizPage.dom.test.tsx LessonPlayerPage.dom.test.tsx && npm run lint && npm run test
```

---

## 2026-05-15 — Frontend Epic 3: teacher module quiz wiring (Course management)

### Completed

- [x] **Course management** — [`frontend/src/pages/CourseManagement.tsx`](frontend/src/pages/CourseManagement.tsx): `loadCourseData` loads `listCourseModuleQuizzes` + `listCourseQuestionBanks` in the same `Promise.all` as course/lessons/modules (fail-whole on error); `createModuleQuiz` for attach with `questionBankUserMessage` on failure and `loadCourseData` refresh on success; `attachingModuleId` busy state.
- [x] **Module quiz panel** — [`frontend/src/components/course/CourseManagementModuleQuizPanel.tsx`](frontend/src/components/course/CourseManagementModuleQuizPanel.tsx): `data-testid="course-management-module-quizzes"`, empty modules copy, per-module join to quiz rows, labeled **Question bank** `<select>` + **Attach quiz** when not linked, empty-banks link to question banks route, read-only bank + served **N** + immutability note when linked.
- [x] **Tests** — [`frontend/src/pages/CourseManagement.dom.test.tsx`](frontend/src/pages/CourseManagement.dom.test.tsx): module quiz wiring describe (section, empty course, attach happy path, 400/409 inline errors).

### Verify

```bash
cd frontend && npm run test -- CourseManagement.dom.test.tsx && npm run lint && npm run knip && npm run build:all && npm run test
```

---

## 2026-05-15 — QB-L Plan 2: publisher GET module-quizzes + POST quiz requires bank

### Completed

- [x] **GET module quizzes** — `GET /courses/{courseId}/module-quizzes`: [`controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py); [`QuestionBankService.list_module_quizzes_for_course`](infrastructure/lambda/catalog/services/question_banks/service.py); [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py) `list_module_quizzes_for_course` (JOIN `course_modules`, order by `module_order` then `module_id`). **200** array of `{ quizId, moduleId, questionBankId, servedCountN, createdAt, updatedAt }`; only rows in `module_quizzes` — no row → omitted from list (aggregate **[]** when none).
- [x] **POST module quiz contract** — `POST …/modules/{moduleId}/quiz` body **must** include `questionBankId` (UUID for bank in this course); missing/blank/invalid/unknown → **400** `bad_request`; bank in another course → **400** with message referencing course mismatch.
- [x] **API Gateway** — [`api-stack.yaml`](infrastructure/templates/api-stack.yaml): `CourseModuleQuizzesResource`, GET + OPTIONS, Cognito; **CatalogApiDeploymentV26** + stage `DeploymentId`.
- [x] **Tests** — integration expectations in [`test_question_bank_publisher_reads.py`](tests/integration/test_question_bank_publisher_reads.py), [`test_question_bank_permissions.py`](tests/integration/test_question_bank_permissions.py); unit routing + service in `tests/unit/services/question_banks/`.
- [x] **Docs** — [`design.md`](design.md) §7; [`plans/architecture/module-map.md`](plans/architecture/module-map.md).

### Verify

```bash
python scripts/check_lambda_boundaries.py
python -m pytest tests/unit/services/question_banks/ -q
```

HTTPS: `pytest tests/integration/test_question_bank_publisher_reads.py tests/integration/test_question_bank_permissions.py -q` with env from [`tests/integration/README.md`](tests/integration/README.md) after deploy applies **V26**.

---

## 2026-05-15 — QB-L: publisher GET question banks + questions

### Completed

- [x] **GET list banks** — `GET /courses/{courseId}/question-banks`: [`controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py); [`QuestionBankService.list_question_banks_for_course`](infrastructure/lambda/catalog/services/question_banks/service.py); [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py) `list_question_banks_for_course`; **200** JSON array `{ questionBankId, status, createdAt, updatedAt }`; empty course **[]**.
- [x] **GET list questions** — `GET /courses/{courseId}/question-banks/{questionBankId}/questions`: same layers + `list_questions_for_publisher` / `list_questions_for_course_bank`; **200** array with `questionId`, `status`, `promptText`, `optionsJson`, `correctOptionKey`; wrong bank → **404** `not_found`.
- [x] **Auth** — [`CourseManagementService.ensure_publisher_question_bank_read`](infrastructure/lambda/catalog/services/course_management/service.py) + [`CourseMutateAuthorizerPort.ensure_course_publisher_read_scope`](infrastructure/lambda/catalog/services/question_banks/ports.py) / [`bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py): same predicate as `_can_manage_course_unenrolled`, **404** on denial (parity with GET modules/lessons on drafts).
- [x] **API Gateway** — [`api-stack.yaml`](infrastructure/templates/api-stack.yaml): `CourseQuestionBanksGetMethod`, `CourseQuestionBankQuestionsGetMethod` (Cognito + AWS_PROXY); **CatalogApiDeploymentV25** + stage `DeploymentId` + `DependsOn`.
- [x] **Tests** — integration: [`tests/integration/test_question_bank_publisher_reads.py`](tests/integration/test_question_bank_publisher_reads.py); helpers [`tests/integration/helpers/api.py`](tests/integration/helpers/api.py) `list_question_banks`, `list_question_bank_questions`. Unit: list GET paths in [`test_question_bank_service.py`](tests/unit/services/question_banks/test_question_bank_service.py); `ensure_publisher_question_bank_read` in [`test_service.py`](tests/unit/services/course_management/test_service.py) `TestEnsurePublisherQuestionBankRead`.
- [x] **Docs** — [`design.md`](design.md) §7 (GET lines + deployment note **V25**).

### Verify

```bash
python scripts/check_lambda_boundaries.py
python -m pytest tests/unit/services/question_banks/ -q
```

HTTPS: `python -m pytest tests/integration/test_question_bank_publisher_reads.py -q` with env from [`tests/integration/README.md`](tests/integration/README.md) after deploy applies **V25** (same bar as other catalog integration tests).

---

## 2026-05-15 — QB-K: instructor question HTTP (post-publish add, PATCH/DELETE)

### Completed

- [x] **§9.1 MCQ add-published** — [`service.py`](infrastructure/lambda/catalog/services/question_banks/service.py) `add_published_question` + [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py) `insert_published_question` with `promptText` / `optionsJson` / `correctOptionKey` validation (unit tests extended).
- [x] **POST overload** — [`controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py): `get_bank_for_course`; same `POST .../questions` branches **DRAFT** vs **PUBLISHED**; **CatalogApiDeploymentV23** in [`api-stack.yaml`](infrastructure/templates/api-stack.yaml).
- [x] **PATCH/DELETE** — `PATCH`/`DELETE` `/courses/{id}/question-banks/{bid}/questions/{qid}`; draft **200**; published **409** `conflict`; **CatalogApiDeploymentV24**; CORS **PATCH** in [`http.py`](infrastructure/lambda/catalog/services/common/http.py).
- [x] **Tests** — integration: [`test_question_bank_post_published_mcq.py`](tests/integration/test_question_bank_post_published_mcq.py), [`test_question_bank_patch_delete.py`](tests/integration/test_question_bank_patch_delete.py); permissions: [`test_question_bank_permissions.py`](tests/integration/test_question_bank_permissions.py); unit controller/service updates.
- [x] **Docs** — [`design.md`](design.md) §7; child plan [`plans/question-banks-qb-k-plan.md`](plans/question-banks-qb-k-plan.md); mega-plan [`plans/question-banks-mega-plan.md`](plans/question-banks-mega-plan.md) **QB-K** row.

### Verify

```bash
python -m pytest tests/unit/services/question_banks/ tests/unit/services/common/test_http.py tests/unit/test_index.py -q
python scripts/check_lambda_boundaries.py
```

HTTPS integration after deploy applies **V24** (see [`tests/integration/README.md`](tests/integration/README.md)).

---

## 2026-05-15 — QB-H / QB-I: submit, grading, latest results, retake

### Completed

- [x] **Migration** — [`infrastructure/database/migrations/010_module_quiz_attempt_submissions.sql`](infrastructure/database/migrations/010_module_quiz_attempt_submissions.sql): `module_quiz_attempt_submissions` (1:1 with submitted attempts; graded answers + counts); listed in apply-schema (**dev + prod**) in [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml).
- [x] **Pure grading** — [`grading.py`](infrastructure/lambda/catalog/services/question_banks/grading.py): equal-weight correct counts vs designated keys (no HTTP).
- [x] **Repo** — [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py): attempt+binding lookups for submit, transactional insert submission + mark submitted, latest submission for binding (for `latest_results` start phase).
- [x] **Service** — [`service.py`](infrastructure/lambda/catalog/services/question_banks/service.py): `submit_module_quiz`; `start_module_quiz` discriminated **`phase`** (`in_progress` | `latest_results`), optional body **`retake`**, **`latestSubmission`** embedding.
- [x] **HTTP contracts** — [`contracts.py`](infrastructure/lambda/catalog/services/question_banks/contracts.py): `StudentQuizSubmitRequestDto` / `StudentQuizSubmitResponseDto`; start unions `StudentQuizStartInProgressDto` / `StudentQuizStartLatestResultsDto`; `StudentQuizStartBodyDto` (`retake`).
- [x] **HTTP** — [`controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py): `POST .../quiz/submit` registered before `quiz/start` before bare `quiz`.
- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml): `CourseModuleQuizSubmitResource` + POST/OPTIONS; **CatalogApiDeploymentV22**.
- [x] **Tests** — unit: [`test_grading.py`](tests/unit/services/question_banks/test_grading.py), [`test_question_bank_submit.py`](tests/unit/services/question_banks/test_question_bank_submit.py), [`test_question_bank_submissions_repo.py`](tests/unit/services/question_banks/test_question_bank_submissions_repo.py), controller submit + updated attempts/start tests; DDL: [`test_question_bank_migration_ddl.py`](tests/unit/test_question_bank_migration_ddl.py) (**010**). Integration **authorship:** [`tests/integration/test_question_bank_submit.py`](tests/integration/test_question_bank_submit.py); helper `submit_module_quiz` in [`tests/integration/helpers/api.py`](tests/integration/helpers/api.py) (HTTPS assertions run in CI after deploy applies template + migrations).
- [x] **Frontend** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) `submitModuleQuiz` + extended `startModuleQuiz` types; [`ModuleQuizPage.tsx`](frontend/src/pages/ModuleQuizPage.tsx) submit + results + retake; [`ModuleQuizPage.dom.test.tsx`](frontend/src/pages/ModuleQuizPage.dom.test.tsx).

### Verify

```bash
pytest tests/unit/services/question_banks/test_grading.py tests/unit/services/question_banks/test_question_bank_submit.py tests/unit/services/question_banks/test_question_bank_submissions_repo.py tests/unit/services/question_banks/test_question_bank_controller_submit.py -q
python scripts/check_lambda_boundaries.py
```

```bash
pytest tests/integration --collect-only -q
```

([`tests/integration/README.md`](tests/integration/README.md) for optional local HTTPS against a deployed stack that includes migration **010** and **CatalogApiDeploymentV22**; do not log JWTs.)

```bash
cd frontend ; npm run test -- src/pages/ModuleQuizPage.dom.test.tsx -q
```

### Scope note

- Breaks implicit client assumption that **any** `POST .../quiz/start` after submit always creates a new attempt: default revisit returns **`phase: latest_results`**; callers must send **`retake: true`** for a new shuffle (documented in [`design.md`](design.md) §7 and [`plans/question-banks-qb-h-plan.md`](plans/question-banks-qb-h-plan.md)). **QB-J** (audit-only) stays future — [`plans/question-banks-mega-plan.md`](plans/question-banks-mega-plan.md).

---

## 2026-05-15 — QB-G: in-progress attempts and presentation shuffle

### Completed

- [x] **Migration** — [`infrastructure/database/migrations/009_module_quiz_attempts.sql`](infrastructure/database/migrations/009_module_quiz_attempts.sql): `module_quiz_attempts` (`in_progress` / `submitted`, `shuffled_question_order`, `shuffled_choice_orders`; one open attempt per binding); bundled in [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) apply-schema (dev + prod).
- [x] **Pure shuffle** — [`presentation_shuffle.py`](infrastructure/lambda/catalog/services/question_banks/presentation_shuffle.py): `shuffle_question_order`, `shuffle_choice_orders_for_questions`, `apply_presentation_shuffle` (injectable `random.Random`).
- [x] **Domain** — [`models.py`](infrastructure/lambda/catalog/services/question_banks/models.py): `ModuleQuizAttempt`, `BoundQuestion`.
- [x] **Repo** — [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py): attempt insert/load (`get_open_attempt`, `get_latest_attempt`, `insert_attempt_with_shuffle`, `mark_attempt_submitted` for tests); concurrent first-open re-read on unique violation (mirror QB-F binding).
- [x] **Service** — [`service.py`](infrastructure/lambda/catalog/services/question_banks/service.py): extended `start_module_quiz` — binding draw unchanged; resolve/create `in_progress` attempt; stable shuffle on re-`start`; QB-F binding-only upgrade creates attempt **1** without redraw.
- [x] **HTTP contract** — [`contracts.py`](infrastructure/lambda/catalog/services/question_banks/contracts.py): `StudentQuizStartDto` adds `attemptId`, `attemptNumber`, `questionIds`.
- [x] **Tests** — [`tests/unit/test_question_bank_migration_ddl.py`](tests/unit/test_question_bank_migration_ddl.py) (009); [`test_presentation_shuffle.py`](tests/unit/services/question_banks/test_presentation_shuffle.py), [`test_question_bank_attempts_repo.py`](tests/unit/services/question_banks/test_question_bank_attempts_repo.py), [`test_question_bank_attempts.py`](tests/unit/services/question_banks/test_question_bank_attempts.py); updated [`test_question_bank_start.py`](tests/unit/services/question_banks/test_question_bank_start.py), [`test_question_bank_controller_start.py`](tests/unit/services/question_banks/test_question_bank_controller_start.py); [`tests/integration/test_question_bank_start.py`](tests/integration/test_question_bank_start.py) (attempt metadata, stable in-progress shuffle).

### Verify

```bash
pytest tests/unit/services/question_banks/test_presentation_shuffle.py tests/unit/services/question_banks/test_question_bank_attempts.py tests/unit/services/question_banks/test_question_bank_attempts_repo.py -q
python scripts/check_lambda_boundaries.py
```

```bash
./scripts/run-local-integration-tests.sh tests/integration/test_question_bank_start.py -q
```

(Requires dev deploy, migrations **008+009**, **CatalogApiDeploymentV21+**, `.env.local` / `LOCAL_COGNITO_PASSWORD` per [`tests/integration/README.md`](tests/integration/README.md); do not log JWTs.)

### Scope note

- **QB-G** adds attempts + shuffle on **QB-F** `POST .../quiz/start`. **Submit**, `latest_results` / **`retake`**, and **`POST .../quiz/submit`** shipped in **2026-05-15 — QB-H / QB-I** above. Earlier plan detail: [`plans/question-banks-qb-g-plan.md`](plans/question-banks-qb-g-plan.md).

---

## 2026-05-15 — QB-F: binding and student start

### Completed

- [x] **Migration** — [`infrastructure/database/migrations/008_student_module_quiz_bindings.sql`](infrastructure/database/migrations/008_student_module_quiz_bindings.sql): `student_module_quiz_bindings` + `student_module_quiz_binding_questions` (per-student draw order; `UNIQUE (module_quiz_id, user_sub)`).
- [x] **Pure draw** — [`infrastructure/lambda/catalog/services/question_banks/binding_draw.py`](infrastructure/lambda/catalog/services/question_banks/binding_draw.py): `draw_question_ids` (`random.sample`; injectable RNG in service).
- [x] **Repo** — [`rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py): `list_published_question_ids`, binding insert/load; concurrent first-start re-read on `UniqueViolation`.
- [x] **Service + ports** — [`service.py`](infrastructure/lambda/catalog/services/question_banks/service.py) `start_module_quiz` (QB-D gate via published course + lesson access); [`ports.py`](infrastructure/lambda/catalog/services/question_banks/ports.py) `StudentLessonAccessPort`, `CourseReadPort`; [`bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py) `_StudentLessonAccessAdapter`, `_CourseReadAdapter`.
- [x] **HTTP** — [`controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py) `POST .../modules/{mid}/quiz/start` (matched **before** `POST .../quiz`); [`contracts.py`](infrastructure/lambda/catalog/services/question_banks/contracts.py) `StudentQuizStartDto` (no `correctOptionKey` / bank ids).
- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml): `CourseModuleQuizStartResource`; deployment **CatalogApiDeploymentV21** (Cognito on POST).
- [x] **Tests** — [`tests/unit/test_question_bank_migration_ddl.py`](tests/unit/test_question_bank_migration_ddl.py) (008); [`test_question_bank_bindings_repo.py`](tests/unit/services/question_banks/test_question_bank_bindings_repo.py), [`test_binding_draw.py`](tests/unit/services/question_banks/test_binding_draw.py), [`test_question_bank_start.py`](tests/unit/services/question_banks/test_question_bank_start.py), [`test_question_bank_controller_start.py`](tests/unit/services/question_banks/test_question_bank_controller_start.py); [`tests/integration/test_question_bank_start.py`](tests/integration/test_question_bank_start.py) (idempotency, 404 gates, leak scan, IDOR).
- [x] **Frontend** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) `startModuleQuiz`; **Start quiz** on [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx) when `moduleQuiz.available`; [`ModuleQuizPage.tsx`](frontend/src/pages/ModuleQuizPage.tsx) behind [`StudentModuleQuizAuth.tsx`](frontend/src/components/auth/StudentModuleQuizAuth.tsx) at `/courses/:courseId/modules/:moduleId/quiz` (prompts + MCQ selection at ship time; submit/results in **QB-H/I** entry above).
- [x] **Response invariants** — `start_module_quiz` returns **409** `conflict` if binding row count or loaded question rows do not match `servedCountN` (never **200** with a short question list).

### Verify

```bash
pytest tests/unit/services/question_banks/ -q
python scripts/check_lambda_boundaries.py
```

```bash
./scripts/run-local-integration-tests.sh tests/integration/test_question_bank_start.py -q
```

(Requires dev deploy, migration **008**, **CatalogApiDeploymentV21+**, `.env.local` / `LOCAL_COGNITO_PASSWORD` per [`tests/integration/README.md`](tests/integration/README.md); do not log JWTs.)

```bash
cd frontend ; npm run test -- src/pages/CourseDetailPage.dom.test.tsx src/pages/ModuleQuizPage.dom.test.tsx
```

### Scope note

- **QB-F** is binding draw + student quiz shell entry; presentation shuffle and attempts shipped in **2026-05-15 — QB-G** above. Submit, scoring, `latest_results`, and **`retake`** shipped in **2026-05-15 — QB-H / QB-I** above.

---

## 2026-05-15 — QB-D: module quiz visibility on course modules list

### Completed

- [x] **Repo** — [`infrastructure/lambda/catalog/services/question_banks/rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py): `list_module_quiz_visibility_for_course` (batch join `module_quizzes` + `question_banks`; published bank + non-null `served_count_n`; course-scoped).
- [x] **Pure gating** — [`infrastructure/lambda/catalog/services/question_banks/visibility.py`](infrastructure/lambda/catalog/services/question_banks/visibility.py): `apply_module_quiz_visibility` (published course + lesson access).
- [x] **Port + wiring** — [`infrastructure/lambda/catalog/services/course_management/ports.py`](infrastructure/lambda/catalog/services/course_management/ports.py) `ModuleQuizVisibilityPort`; [`bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py) `_ModuleQuizVisibilityAdapter`; [`service.py`](infrastructure/lambda/catalog/services/course_management/service.py) `list_course_modules_public` adds optional `moduleQuiz` on module rows; [`contracts.py`](infrastructure/lambda/catalog/services/course_management/contracts.py) `ModuleQuizDto`.
- [x] **Tests** — [`tests/unit/services/question_banks/test_question_bank_visibility.py`](tests/unit/services/question_banks/test_question_bank_visibility.py); repo visibility cases in [`test_question_bank_rds_repo.py`](tests/unit/services/question_banks/test_question_bank_rds_repo.py); [`tests/unit/test_course_management_service.py`](tests/unit/test_course_management_service.py); [`tests/unit/test_bootstrap.py`](tests/unit/test_bootstrap.py) (`TestModuleQuizVisibilityAdapter`); [`tests/integration/test_question_bank_visibility.py`](tests/integration/test_question_bank_visibility.py) (6 scenarios: draft bank, published+enrolled, unenrolled, owner without enrollment, leak scan, student publish denied).
- [x] **Frontend** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) `CourseModule.moduleQuiz`; passive **Module quiz** badge on [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx) when enrolled and `moduleQuiz.available` (no Start control).
- [x] **Docs** — [`design.md`](design.md) course-modules API + §13; [`plans/architecture/module-map.md`](plans/architecture/module-map.md).

### Verify

```bash
pytest tests/unit/services/question_banks/test_question_bank_visibility.py tests/unit/test_course_management_service.py -q
```

```bash
./scripts/run-local-integration-tests.sh tests/integration/test_question_bank_visibility.py -q
```

(Requires dev deploy, `.env.local` / `LOCAL_COGNITO_PASSWORD` per [`tests/integration/README.md`](tests/integration/README.md); do not log JWTs.)

```bash
cd frontend && npm run test -- src/pages/CourseDetailPage.dom.test.tsx -q
```

### Scope note

- **QB-D** is visibility/gating + passive badge only. **QB-F** (first start, binding, student shell) shipped in the **2026-05-15 — QB-F** entry above.

---

## 2026-05-15 — QB-C/E hardening: MCQ validation + test coverage

### Completed

- [x] **MCQ validation** — [`infrastructure/lambda/catalog/services/question_banks/mcq_validation.py`](infrastructure/lambda/catalog/services/question_banks/mcq_validation.py): `optionsJson` must include ≥1 choice with a `key`; when set, `correctOptionKey` must match a choice key; used on draft create, publish (service), and inside [`publish_bank_transaction`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py).
- [x] **Service** — [`service.py`](infrastructure/lambda/catalog/services/question_banks/service.py): `update_question` accepts optional fields with merged validation; `courseId` checked on update/delete.
- [x] **Unit tests** — [`tests/unit/services/question_banks/test_mcq_validation.py`](tests/unit/services/question_banks/test_mcq_validation.py), expanded [`test_question_bank_service.py`](tests/unit/services/question_banks/test_question_bank_service.py), [`test_question_bank_rds_repo.py`](tests/unit/services/question_banks/test_question_bank_rds_repo.py) (`publish_bank_transaction` TX paths), [`test_question_bank_controller.py`](tests/unit/services/question_banks/test_question_bank_controller.py).
- [x] **Integration tests** — [`tests/integration/test_question_bank_publish.py`](tests/integration/test_question_bank_publish.py): publish without linked module quiz (**400**), double publish (**409**); [`tests/integration/helpers/api.py`](tests/integration/helpers/api.py) `create_module_quiz(..., question_bank_id=...)`, `create_draft_question`, `publish_question_bank`.
- [x] **Docs** — [`design.md`](design.md) §7/§13, [`roadmap.md`](roadmap.md) MVP baseline + bridge row 4 synced.

---

## 2026-05-14 — QB-C / QB-E: `questions` migration, publish + N, draft create HTTP

### Completed

- [x] **Migration** — [`infrastructure/database/migrations/007_question_bank_questions.sql`](infrastructure/database/migrations/007_question_bank_questions.sql): `questions` (composite FK to `question_banks`, `DRAFT`/`PUBLISHED`, MCQ JSON + `correct_option_key`); bundled in [`scripts/deploy-rds-stack.sh`](scripts/deploy-rds-stack.sh), [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml), [`infrastructure/deploy.ps1`](infrastructure/deploy.ps1) with **006**.
- [x] **Service** — [`infrastructure/lambda/catalog/services/question_banks/service.py`](infrastructure/lambda/catalog/services/question_banks/service.py): `publish_question_bank` (§9.3 / §5 validation + auth), `create_draft_question`, `add_published_question`, `update_question`, `delete_question` (published immutable).
- [x] **Repo** — [`infrastructure/lambda/catalog/services/question_banks/rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py): draft CRUD, `publish_bank_transaction` (single TX, bank `FOR UPDATE`, flips drafts → `PUBLISHED`, bank → `PUBLISHED`, `module_quizzes.served_count_n = n`).
- [x] **HTTP** — [`infrastructure/lambda/catalog/services/question_banks/controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py): `POST .../question-banks/{bid}/questions`, `POST .../publish` (+ OPTIONS); [`infrastructure/lambda/catalog/services/common/validation.py`](infrastructure/lambda/catalog/services/common/validation.py) `require_json_array_or_object`.
- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml): nested resources; deployment **CatalogApiDeploymentV20** (Cognito on new `POST` methods).
- [x] **Tests** — [`tests/unit/services/question_banks/test_question_bank_service.py`](tests/unit/services/question_banks/test_question_bank_service.py); [`tests/unit/test_question_bank_migration_ddl.py`](tests/unit/test_question_bank_migration_ddl.py); [`tests/unit/test_rds_schema_apply.py`](tests/unit/test_rds_schema_apply.py); [`tests/integration/helpers/api.py`](tests/integration/helpers/api.py); [`tests/integration/test_question_bank_publish.py`](tests/integration/test_question_bank_publish.py). *(Further MCQ/repo/controller tests: **2026-05-15** entry above.)*

### Ops / verify

- **Local HTTPS** against **current dev**: run [`./scripts/run-local-integration-tests.sh`](./scripts/run-local-integration-tests.sh) `tests/integration/test_question_bank_publish.py` **after** dev has **API deployment V20** (or newer) and RDS schema includes **007**; otherwise `POST .../questions` / `.../publish` can return API Gateway **403** (“Invalid key=value pair … Authorization header”) because the stage snapshot predates the Cognito methods.

### Scope note

- **QB-D** (student quiz visibility / §6–7) shipped in the **2026-05-15 — QB-D** entry above. **QB-F+** (binding, attempts) was **not** this slice.

---

## 2026-05-14 — QB-B: Question bank + module quiz create APIs (publisher authz)

### Completed

- [x] **Port + service** — [`infrastructure/lambda/catalog/services/question_banks/ports.py`](infrastructure/lambda/catalog/services/question_banks/ports.py) (`CourseMutateAuthorizerPort`), [`.../service.py`](infrastructure/lambda/catalog/services/question_banks/service.py) (`QuestionBankService`: authorizer before RDS; IDOR guard when `questionBankId` is supplied).
- [x] **Composition root** — [`infrastructure/lambda/catalog/bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py): `_CourseMutateAuthorizerAdapter` delegates to `CourseManagementService.ensure_can_modify_course`; `AwsDeps.question_bank_service`; `lambda_bootstrap` fifth return value.
- [x] **HTTP** — [`infrastructure/lambda/catalog/services/question_banks/controller.py`](infrastructure/lambda/catalog/services/question_banks/controller.py); [`infrastructure/lambda/catalog/index.py`](infrastructure/lambda/catalog/index.py) dispatches before `course_management_handle`.
- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml): `POST` + `OPTIONS` on `/courses/{courseId}/question-banks` and `/courses/{courseId}/modules/{moduleId}/quiz` (Cognito for `POST`); deployment bumped **V18 → V19**.
- [x] **Tests** — [`tests/unit/services/question_banks/test_question_bank_service.py`](tests/unit/services/question_banks/test_question_bank_service.py) (authorizer ordering); [`tests/integration/test_question_bank_permissions.py`](tests/integration/test_question_bank_permissions.py) (owner **201** for bank + module-quiz create; alt teacher **403** + `code: forbidden`; student **401/403** + `unauthorized`/`forbidden` for **both** routes); [`tests/integration/helpers/api.py`](tests/integration/helpers/api.py) (`create_question_bank`, `create_module_quiz`); [`tests/unit/test_bootstrap.py`](tests/unit/test_bootstrap.py) / [`tests/unit/test_index.py`](tests/unit/test_index.py) / [`tests/unit/test_index_logging.py`](tests/unit/test_index_logging.py) (`lambda_bootstrap` fifth tuple element).

### Scope note

- **QB-B** covered create bank + module quiz only. **QB-C/QB-E** (publish, `questions`, `served_count_n`, draft HTTP) are in the **2026-05-14 — QB-C / QB-E** entry above. **QB-D** (student visibility) shipped **2026-05-15** (entry above).

---

## 2026-05-14 — QB-A: RDS `question_banks` + `module_quizzes` + repository

### Completed

- [x] **Migration** — [`infrastructure/database/migrations/006_question_banks_module_quizzes.sql`](infrastructure/database/migrations/006_question_banks_module_quizzes.sql): course-scoped `question_banks` (`DRAFT` / `PUBLISHED`), `module_quizzes` with `UNIQUE(module_id)`, nullable `served_count_n` (≥1 when set), composite `FOREIGN KEY (course_id, question_bank_id)` → `question_banks(course_id, id)` for cross-course attach prevention.
- [x] **Deploy bundle** — [`scripts/deploy-rds-stack.sh`](scripts/deploy-rds-stack.sh) and [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) concatenate **006** into `schema.sql` alongside 001+003+004.
- [x] **Catalog adapter** — [`infrastructure/lambda/catalog/services/question_banks/rds_repo.py`](infrastructure/lambda/catalog/services/question_banks/rds_repo.py): `QuestionBankRdsRepository` (`insert_question_bank`, `insert_module_quiz`, getters); maps `UniqueViolation` → `Conflict`, `ForeignKeyViolation` → `BadRequest`.
- [x] **Tests** — [`tests/unit/test_question_bank_migration_ddl.py`](tests/unit/test_question_bank_migration_ddl.py), [`tests/unit/services/question_banks/test_question_bank_rds_repo.py`](tests/unit/services/question_banks/test_question_bank_rds_repo.py), [`tests/unit/test_rds_schema_apply.py`](tests/unit/test_rds_schema_apply.py) (006 split + concatenated bundle).
- [x] **CI boundaries** — [`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py) allows `psycopg2` in `question_banks/rds_repo.py`.
- [x] **Docs** — [`plans/architecture/module-map.md`](plans/architecture/module-map.md) `services/question_banks/` row; [`design.md`](design.md) §13 RDS / near-term row (question banks schema + follow-on HTTP).

### Scope note

- **HTTP / API Gateway:** `POST /courses/{id}/question-banks` and `POST /courses/{id}/modules/{mid}/quiz` shipped in **QB-B** (2026-05-14 entry above); QB-A delivered schema + repository only.

---

## 2026-05-09 — Site-wide cool theme + lesson player shell refresh (frontend-only)

### Completed

- [x] **Design tokens / canvas** — [`frontend/src/style.css`](frontend/src/style.css): cool neutrals, blue-tinted borders; fixed radial washes on `body`; [`frontend/src/components/layout/Layout.tsx`](frontend/src/components/layout/Layout.tsx) uses a transparent main shell so the canvas shows through.
- [x] **Chrome** — [`frontend/src/components/layout/Footer.tsx`](frontend/src/components/layout/Footer.tsx) light gradient footer; [`frontend/src/student-app/StudentHeader.tsx`](frontend/src/student-app/StudentHeader.tsx) and [`frontend/src/teacher-app/TeacherHeader.tsx`](frontend/src/teacher-app/TeacherHeader.tsx) opaque white headers; [`frontend/tailwind.config.js`](frontend/tailwind.config.js) slightly softer `dot-grid`.
- [x] **Lesson playback** — [`frontend/src/pages/LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx): professional blue lesson UI (sidebar, alerts, toolbar, primary column), shared progress gradient constants, subtler video container (no heavy bezel).

### Scope note

- **Backend / Lambda / API:** unchanged.

---

## 2026-05-09 — Student SPA: Home (`/`), catalog at `/catalog`, My Course hub, course detail + pricing UI (frontend-only)

### Completed

- [x] **Routing** — Student shell: dedicated **Home** at **`/`**; published course grid moved to **`/catalog`**; signed-in **My Course** hub at **`/my-course`** (course detail and lesson player paths unchanged: **`/courses/:courseId`**, **`/courses/:courseId/lessons/:lessonId`**).
- [x] **Course detail** — Visual/styling refresh on the student course detail page; **pricing** UI extracted into a reusable section component (still **MVP-free** presentation; no new backend pricing or checkout).
- [x] **Figma gap tracking** — New **`TODO(figma-backend) GAP-S2-…`** IDs in student UI with a single normative row table in **[`reports/figma-student-ui-gap-report.md`](reports/figma-student-ui-gap-report.md)** (shared mock literals in **`frontend/src/lib/figma-mocks.ts`**; do not duplicate the report table here).

### Scope note

- **Backend / Lambda / API:** unchanged in this slice (documentation only here; implementation was frontend-only).

---

## 2026-05-08 — Public catalog GETs: permissive REQUEST authorizer + `/review` evidence bar + commit HTTPS guidance

### API stack (`infrastructure/templates/api-stack.yaml`)

- **`CatalogApiPublicReadAuthorizer`** — `REQUEST` Lambda authorizer (same **`catalog_token_authorizer`** zip as **`TokenAuthorizerLambda`**): permissive **`Allow`** with anonymous context when `Authorization` missing/invalid/non–id-token; valid Cognito Id token → **`sub`** / **`role`** / **`email`** in API Gateway **`context`**.
- **GET wiring** — `GET /courses/{courseId}`, `GET …/modules`, `GET …/lessons` use **`AuthorizationType: CUSTOM`** + **`AuthorizerId`** above (replacing pool-only auth on those reads so anonymous catalog works without Gateway 401, while Bearer still hydrates Lambda claims).
- **Deployment** — Logical id bumps **`CatalogApiDeploymentV14` → … → `V18`** with **`DependsOn`** including the public-read authorizer so the stage picks up snapshot changes.
- **`IdentitySource`** (**follow-up**) — **`method.request.header.Authorization`** caused API Gateway to return **401** without invoking the Lambda when the header was absent (anonymous catalog). **`method.request.path.courseId`** is **not allowed** by API Gateway REQUEST authorizers (only header/query/stage/context). Use **`method.request.header.Host`** (always present); handler still reads **`Authorization`** from the full request when present. **`AuthorizerResultTtlInSeconds: 0`** — cache key uses identity sources only (**Host** alone would otherwise collapse TTL>0 caches across callers) (**cfn-lint** clean).

### Cursor

- **[`.cursor/commands/review.md`](.cursor/commands/review.md)** — Expanded **evidence-only** rule: severity labels require demonstrable defects; forbid hypothetical “might/could” padding; **`Out of scope`** tail without severity.
- **[`.cursor/skills/review-and-commit/SKILL.md`](.cursor/skills/review-and-commit/SKILL.md)** — Phase 1 aligns with **`/review`**; severity quick-reference applies only when evidence-backed.
- **[`.cursor/skills/commit/SKILL.md`](.cursor/skills/commit/SKILL.md)** — When **`./scripts/run-local-integration-tests.sh`** may be omitted: deploy mismatch vs **dev**, user waiver, typo-only Markdown; distinguishes static **`pytest --collect-only`** from HTTPS live-dev tests.

---

## 2026-05-08 — Cognito JWT audience deploy + Gateway claims fallback + `/review` command

### Auth / catalog

- **[`services/common/http.py`](infrastructure/lambda/catalog/services/common/http.py)** — `_claims_with_principal_fallback`: when **`requestContext.authorizer.sub`** is empty, copy **`principalId`** into **`sub`** (gateway-trusted); tolerate non-dict authorizer payloads.
- **[`catalog_token_authorizer/index.py`](infrastructure/lambda/catalog_token_authorizer/index.py)** — Document and keep **IdToken-only** JWT validation (**`token_use == id`**): pool **access tokens** typically omit **`custom:role`**; accepting them mapped callers to **`student`** and diverged from Id-token RBAC.

### Deploy

- **`scripts/deploy-backend.sh`** — Resolve **`TeacherUserPoolClientId`** and **`StudentUserPoolClientId`** from **`StreamMyCourse-Auth-${ENV}`**, pass **`CognitoClientId`** as CSV to the API stack; stderr **Warning** / **Note** when the parameter override is omitted (stack keeps prior value).

### Tests

- [`tests/unit/services/common/test_http.py`](tests/unit/services/common/test_http.py) — flattened and nested **`authorizer`** + **`principalId`** cases.
- [`tests/unit/services/token_authorizer/test_token_authorizer.py`](tests/unit/services/token_authorizer/test_token_authorizer.py) — access JWT → empty context; unknown **`token_use`** (e.g. refresh) unchanged.

### Tooling

- [`.cursor/commands/review.md`](.cursor/commands/review.md) — project **`/review`** command (severity-only findings, no hypothetical futures as ranked issues).
- [`.cursor/skills/review-and-commit/SKILL.md`](.cursor/skills/review-and-commit/SKILL.md) — links review-only flows to **`/review`** (**`../../commands/review.md`**).

---

## 2026-05-08 — Authorization hardening: createdBy invariant + privilege-escalation fix

### Security fix

- **Privilege escalation (now closed):** `_can_manage_course_unenrolled` previously returned `True` for any teacher when `createdBy` was blank, letting any teacher read draft lessons, bypass the enrollment gate for playback, and appear as the owner in `ensure_can_modify_course`. The same blank-owner path in `ensure_can_modify_course` returned early (allow). Both are now `Forbidden`/`BadRequest` respectively; blank `createdBy` is now treated as a data-integrity error, not a grant of universal teacher access.

---

## 2026-05-08 — Auth: remove in-VPC JWT verification (REQUEST authorizer)

### Why

- The catalog Lambda runs in a private VPC subnet without internet egress; JWKS fetch/token verification inside the Lambda caused timeouts on public read routes when callers supplied `Authorization` headers.

### What shipped

- **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml)
  - `CatalogApiTokenAuthorizer` switched to **`Type: REQUEST`**
  - Public GET methods now use **`AuthorizationType: CUSTOM`** with the permissive authorizer:
    - `GET /courses`
    - `GET /courses/{id}`
    - `GET /courses/{id}/modules`
    - `GET /courses/{id}/lessons`
- **Token authorizer Lambda** — [`infrastructure/lambda/catalog_token_authorizer/index.py`](infrastructure/lambda/catalog_token_authorizer/index.py)
  - Reads bearer token from `event.headers.Authorization` (REQUEST event shape), still **Allow**-by-default with empty context for anonymous/invalid tokens.
- **Catalog Lambda (in VPC)** — `infrastructure/lambda/catalog/`
  - Deleted `services/common/jwt_verify.py` and removed the Authorization-header fallback from `services/common/http.py`
  - Removed Cognito JWT config parsing/wiring from `config.py` and `index.py`
  - Dropped `cryptography` from `infrastructure/lambda/catalog/requirements.txt`

### What shipped

- **`Course.createdBy`** promoted to a required positional field (no `= ""` default). Any construction without an owner now fails at the Python type level rather than silently producing phantom ownership.
- **`CourseCatalogRepositoryPort.create_course`** — `created_by` parameter loses its `= ""` default.
- **`rds_repo.py`** — `_row_to_course` uses `str(created_by or "")` (consistent defensive coercion); `_create_course_atomic` drops the `or ""` fallback since the DB column is now `NOT NULL`.
- **`001_initial_schema.sql`** — `courses.created_by` changed from `NOT NULL DEFAULT ''` to `NOT NULL` + `CONSTRAINT courses_created_by_not_blank CHECK (btrim(created_by) <> '')` for fresh installs.
- **`004_enforce_course_created_by.sql`** — In-place upgrade for existing DBs. Uses a `DO $$ ... $$` block that emits a `RAISE WARNING` and skips `ADD CONSTRAINT` instead of aborting deployment when blank-owner rows exist; operators must repair those rows and redeploy.
- **`rds_schema_apply/index.py`** — `_split_sql_statements` upgraded from naive `;` split to a character-level scanner that respects `$$` dollar-quoted blocks, enabling PL/pgSQL `DO` blocks in future migrations.
- **`scripts/migrate-dynamodb-to-rds.py`** — Deleted (one-shot DynamoDB→RDS migration complete).
- **Service comments** — `get_course_detail_with_enrollment` documents that `enrolled` means "has lesson access" (True for enrolled students, owner-teachers, and admins) to clarify the intentional overloading of the field name.

### Test coverage added

- `TestListCourseModulesPublic` — 6 new cases (previously zero coverage for this service method).
- `TestEnsureCanViewLessonsAndPlayback.test_anonymous_blank_sub_raises_forbidden` — pins that blank sub is always denied playback at the service layer.
- `TestGetCourseDetailPublicCatalog` — non-owner teacher on draft → NotFound; admin on draft → sees it with `enrolled=True`.
- `TestListLessonsPublic` — non-owner teacher on draft → NotFound; admin on draft → returns lessons.
- `test_rds_schema_apply.py` — two new splitter tests for `$$` dollar-quote handling; 004 migration test updated for the DO-block structure.

---

## 2026-05-07 — Course modules: HTTPS integration + API deploy + schema tightening

### Completed

- [x] **Integration coverage** — [`tests/integration/test_course_modules.py`](tests/integration/test_course_modules.py) (modules CRUD/sort, lesson `moduleId`, draft parity, publish + student `GET …/modules`, negatives). Helpers: [`tests/integration/helpers/module_contract.py`](tests/integration/helpers/module_contract.py). Extended [`tests/integration/test_access_control.py`](tests/integration/test_access_control.py), [`tests/integration/test_student_permissions_denials.py`](tests/integration/test_student_permissions_denials.py), [`tests/integration/test_rds_path.py`](tests/integration/test_rds_path.py); README module + troubleshooting bullets ([`tests/integration/README.md`](tests/integration/README.md)).

- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml): module REST resources/methods wired into **`CatalogApiDeploymentV10`** `DependsOn`; stage **`DeploymentId`** updated (`V9` → `V10`) so template-only route changes replace the stage snapshot.

- [x] **Schema (`001`)** — [`infrastructure/database/migrations/001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql): **`UNIQUE (course_id, id)`** on **`course_modules`**; **`lessons`** use **`FOREIGN KEY (course_id, module_id) REFERENCES course_modules (course_id, id)`**. Operator note in-file for older DBs.

- [x] **Catalog** — Default module row title **`Overview`** on course create ([`rds_repo.py`](infrastructure/lambda/catalog/services/course_management/rds_repo.py)). **`as_lesson_dto`** requires non-empty **`moduleId`** and **`moduleOrder`** ([`contracts.py`](infrastructure/lambda/catalog/services/course_management/contracts.py)).

- [x] **Module delete semantics** — `DELETE /courses/{id}/modules/{mid}` is **idempotent** for unknown ids (`200` + `deleted: false`) and rejects deleting the last module (`400`).

- [x] **Docs** — [`design.md`](design.md) **`CatalogApiDeploymentV10`** + module-delete / media-queue **503** note.

---

## 2026-05-07 — Frontend: course modules in student + teacher SPA

### Completed

- [x] **API client** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts): `listCourseModules`, `createCourseModule`, `deleteCourseModule`, lesson create body supports optional `moduleId` (ordering per API).
- [x] **Teacher** — [`frontend/src/pages/CourseManagement.tsx`](frontend/src/pages/CourseManagement.tsx): draft-only **Modules / Sections** panel (create with title/description, delete non-last module); **Add Lesson** supports optional **`moduleId`** when the course has more than one module.
- [x] **Student** — [`frontend/src/pages/CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx) and [`frontend/src/pages/LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx): lessons listed under module headers; ordering uses `moduleOrder` then `order`; combined course load surfaces an error if **`GET /courses/{id}/modules`** fails (empty lists + message); removed redundant per-row “Lesson N” subtitle so the title line is not duplicated.

---

## 2026-05-06 — Developer experience: Vitest coverage, teacher Vite parity, Cognito localhost callbacks

### Completed

- [x] **Vitest coverage (opt-in)** — [`frontend/package.json`](frontend/package.json) **`test:coverage`**, devDependency [`@vitest/coverage-v8`](frontend/package.json); [`frontend/vitest.config.ts`](frontend/vitest.config.ts): **`coverage.enabled: false`** by default (**`vitest run --coverage`** opt-in, v8 **text-summary** / **json-summary**); **`frontend/coverage/`** gitignored ([`frontend/.gitignore`](frontend/.gitignore)). Pre-merge note in [`AGENTS.md`](AGENTS.md).

- [x] **Teacher dev server SPA entry** — [`frontend/vite.teacher.config.ts`](frontend/vite.teacher.config.ts): dev middleware serves **`teacher.html`** for document navigations (so **`/`** matches production teacher SPA instead of falling through to student **`index.html`**).

- [x] **Cognito Hosted UI local URLs** — [`infrastructure/templates/auth-stack.yaml`](infrastructure/templates/auth-stack.yaml): default **student / teacher** **CallbackUrls** + **LogoutUrls** include **`127.0.0.1`** alongside **`localhost`** (ports **5173** / **5174**); runbook **§ `error=redirect_mismatch`** + LAN caveats in [`infrastructure/docs/admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md); **`frontend/.env.example`** Hosted UI bullets cross-reference [`frontend/src/lib/auth.ts`](frontend/src/lib/auth.ts).

- [x] **Dispatch dev backend-only deploy via GitHub** — [`scripts/backend-dev/README.md`](scripts/backend-dev/README.md) + [`Backend-dev-via-GitHub.sh`](scripts/backend-dev/Backend-dev-via-GitHub.sh) / [`.ps1`](scripts/backend-dev/Backend-dev-via-GitHub.ps1): `gh workflow run` for **[`deploy-backend-dev-only.yml`](.github/workflows/deploy-backend-dev-only.yml)** (video + Cognito auth + `./scripts/deploy-backend.sh dev`), using Environment **dev** secrets on GitHub — no AWS creds pulled locally.

---

## 2026-05-06 — Frontend: course load hardening, Unsorted lessons, code-first API errors

### Completed

- [x] **CourseManagement loader** — [`frontend/src/pages/CourseManagement.tsx`](frontend/src/pages/CourseManagement.tsx): on failed load, clear course, lessons, modules, editor fields, and module selection so a `:courseId` change cannot leave stale form data; **404** uses `notFound` + existing not-found UI; other errors use a dedicated **`ErrorView`** (message + back) instead of masking as “Course not found”; **`void`**-wrap **`handleDeleteLesson`** in JSX. Coverage: [`CourseManagement.dom.test.tsx`](frontend/src/pages/CourseManagement.dom.test.tsx).

- [x] **Student pages** — [`frontend/src/pages/CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx) and [`frontend/src/pages/LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx): **`setCourse(null)`** on load failure (player also clears video **`src`** where applicable) so failed navigation does not show the previous course in hero, breadcrumb, or player. Coverage: [`CourseDetailPage.dom.test.tsx`](frontend/src/pages/CourseDetailPage.dom.test.tsx), [`LessonPlayerPage.dom.test.tsx`](frontend/src/pages/LessonPlayerPage.dom.test.tsx).

- [x] **`lessonGrouping` + Unsorted** — [`frontend/src/lib/lessonGrouping.ts`](frontend/src/lib/lessonGrouping.ts) groups lessons by known modules; lessons with a **`moduleId`** not returned by **`GET /courses/{id}/modules`** appear under an **Unsorted** section on detail and player (no silent drop). Unit tests: [`lessonGrouping.test.ts`](frontend/src/lib/lessonGrouping.test.ts).

- [x] **Code-first error classification** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts): **`isLastModuleDeleteError`** and **`isMediaCleanupUnavailableError`** check **`ApiError.code`** first (`last_module_required`, `media_cleanup_unavailable`), then fall back to status + message regex. Tests: [`api.test.ts`](frontend/src/lib/api.test.ts).

---

## 2026-05-06 — Integration Test Suite: 95 Tests + UUID Validation + Multi-Principal Security

### Completed

- [x] **Integration Test Suite** — 95 HTTPS integration tests (consolidated from 100 via parameterization):
  - `test_access_control.py` — 8 parameterized IDOR/BOLA cross-teacher security tests
  - `test_auth_gateway.py` — Cognito authorizer + API Gateway integration
  - `test_bootstrap_edges.py` — Lambda cold-start, CORS, malformed input handling
  - `test_course_thumbnail.py` — Thumbnail upload/presigned URL tests
  - `test_courses.py` — Course CRUD + lesson update tests
  - `test_enrollment.py` — Enrollment flow, idempotency, draft rejection, 404 handling
  - `test_instructor_dashboard.py` — `/courses/mine` endpoint + sorting tests
  - `test_lesson_not_found.py` — 7 tests for non-existent lesson ID 404 responses
  - `test_lesson_ordering.py` — Lesson sequence integrity
  - `test_playback_auth.py` — 4 enrollment-gated playback authorization tests
  - `test_playback_upload.py` — Upload URL generation + content-type validation
  - `test_progress.py` — 7 progress tracking + aggregation tests
  - `test_publish.py` — Draft/publish workflow, idempotency, validation edge cases
  - `test_rds_path.py` — RDS connectivity (removed 1 duplicate test)
  - `test_s3_cleanup.py` — S3 media deletion via SQS worker
  - `test_student_permissions_allowed.py` — 5 positive student permission tests
  - `test_student_permissions_denials.py` — 10 parameterized student→instructor denial tests

- [x] **Backend UUID Validation** — [`infrastructure/lambda/catalog/services/course_management/service.py`](infrastructure/lambda/catalog/services/course_management/service.py):
  - Added `_is_valid_uuid()` helper with `UUID` stdlib validation
  - 16 public methods now validate UUID format before database queries
  - Returns 404 `not_found` for malformed IDs instead of 500 `internal_error`
  - Prevents PostgreSQL type errors on invalid input

- [x] **Unit Test Additions** — [`tests/unit/test_integration_api_client.py`](tests/unit/test_integration_api_client.py): API client contract validation + 23 new UUID validation tests in [`test_service.py`](tests/unit/services/course_management/test_service.py)

- [x] **Multi-Principal Test Infrastructure** — [`tests/integration/conftest.py`](tests/integration/conftest.py):
  - `alt_api` fixture — Teacher B for cross-user access control tests
  - `student_api` fixture — Student principal for permission tests
  - `alt_course_factory`, `alt_lesson_factory` — Teacher B resource creation
  - `enrolled_course` fixture — Published course with student enrollment
  - Multi-principal cleanup: safety net cleans up for ALL 3 principals

- [x] **Test Parameterization** — Reduced test count from 100→88 (now 95) while maintaining coverage:
  - 10 student denial tests → 1 parameterized test
  - 8 IDOR tests → 1 parameterized test  
  - 2 upload-url validation tests → 1 parameterized test

- [x] **3-Principal CI Matrix** — GitHub Actions workflow [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) orchestrates:
  1. **dev** — Edge + RDS + Backend deploy on main push
  2. **integration** — HTTPS pytest against dev (95 integration tests)
  3. **verify-rds** — Database verification with Cognito credentials
  4. **prod** — Sequential prod deploy only after dev + tests pass

- [x] **Security Test Coverage** — Cross-cutting validations:
  - Authentication: Token handling, missing Authorization header
  - Authorization: IDOR (Teacher A → Teacher B), BFLA (Student → Instructor), role boundaries
  - Input validation: UUID format, SQL injection resistance, path traversal
  - CORS: Preflight handling, origin enforcement
  - Presigned URLs: Scoping, content-type restrictions

### Technical Notes

- Integration tests require `LOCAL_COGNITO_PASSWORD` + `LOCAL_COGNITO_PASSWORD_ALT` + `LOCAL_COGNITO_PASSWORD_STUDENT` in `.env.local`
- Test helpers in [`tests/integration/helpers/api.py`](tests/integration/helpers/api.py): `ApiClient` with methods for all catalog endpoints
- All integration tests run against **deployed** dev environment (no local mocks)
- Cleanup: Per-test finalizers + session-end safety net with dual-prefix support (`integration-test-` and `[TEST]`)
- CI gate: Prod deploy blocked if any of 95 integration tests fail

---

## 2026-05-06 — MVP Phase Complete

### Completed

- [x] **MVP Core Features**
  - Course catalog (browse, search) — [`CourseCatalogPage.tsx`](frontend/src/pages/CourseCatalogPage.tsx)
  - Course detail with lesson list — [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx)
  - Video playback with progress tracking — [`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx)
  - Instructor dashboard and course management — [`InstructorDashboard.tsx`](frontend/src/pages/InstructorDashboard.tsx), [`CourseManagement.tsx`](frontend/src/pages/CourseManagement.tsx)
  - Draft/publish workflow — [`PUT /courses/{id}/publish`](infrastructure/lambda/catalog/services/course_management/controller.py)
  - S3 presigned upload/playback — [`upload-url`](infrastructure/lambda/catalog/services/course_management/controller.py), [`playback`](infrastructure/lambda/catalog/services/playback/controller.py)
- [x] **Authentication** — Cognito with Google-only federation; [`auth-stack.yaml`](infrastructure/templates/auth-stack.yaml), [`SignIn.tsx`](frontend/src/components/auth/SignIn.tsx)
- [x] **Data Layer** — RDS PostgreSQL (`db.t4g.micro`) with VPC; [`rds-stack.yaml`](infrastructure/templates/rds-stack.yaml); fully migrated from DynamoDB per [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md)
- [x] **Lesson Progress Tracking** — 15s heartbeat + circuit breaker + checkpoints; [`services/progress/`](infrastructure/lambda/catalog/services/progress/) per [ADR-0010](plans/architecture/adr-0010-lesson-progress-rds.md)
- [x] **Media Cleanup** — Async S3 deletion via SQS worker; [`media-cleanup-stack.yaml`](infrastructure/templates/media-cleanup-stack.yaml)
- [x] **CI/CD** — GitHub Actions: [`ci.yml`](.github/workflows/ci.yml), [`deploy-backend.yml`](.github/workflows/deploy-backend.yml); OIDC deploy role [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml)
- [x] **Security** — CORS hardened, presigned URL scoping, security headers, DeletionPolicy: Retain on all stateful resources

### Phase 2 Ready

All MVP backlog items from [design.md §13](./design.md) are complete:
1. Video CDN (CloudFront + OAC) — shipped
2. Frontend hosting (dual SPAs on S3 + CloudFront + Route 53) — shipped
3. Auth (Cognito + Google IdP + API authorizer) — shipped
4. RDS PostgreSQL (catalog + lesson_progress) — shipped

### Next Phase

Per [roadmap.md](./roadmap.md):
- Security scanning in CI
- Automated dependency upgrades
- Phase 2 monetization (Stripe, Kinescope DRM, reviews, analytics)

---

## 2026-05-05 — Progress tracking: 15s heartbeat, circuit breaker, checkpoints

### Completed

- [x] **15-second heartbeat throttle** — Changed from 12s to 15s minimum between progress update attempts; tracks last attempt time (not success time) to prevent failure-induced Lambda spam ([`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx)).
- [x] **Circuit breaker** — After 10 consecutive failures, progress updates stop until page refresh; prevents runaway Lambda costs during outages ([`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx)).
- [x] **Pause checkpoint** — Video `pause` event triggers immediate progress save (ignores 15s throttle, respects circuit breaker) ([`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx)).
- [x] **Visibility checkpoint** — `visibilitychange` to `hidden` triggers immediate save (tab switch / minimize) ([`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx)).
- [x] **Pagehide checkpoint** — `pagehide` event triggers best-effort save on tab close ([`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx)).
- [x] **Consistent failure handling** — `handleVideoEnded` and `handleMarkIncomplete` now use same circuit breaker pattern as heartbeat/checkpoints ([`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx)).
- [x] **Tests** — 6 new Vitest DOM tests: circuit breaker (2 tests), 15s throttle, pause checkpoint, visibility checkpoint, pagehide checkpoint, markIncomplete failure path ([`LessonPlayerPage.dom.test.tsx`](frontend/src/pages/LessonPlayerPage.dom.test.tsx)).

### Technical notes

- CORS verified working for progress endpoint (`OPTIONS` at `/courses/{id}/lessons/{lid}/progress` returns proper headers)
- Used `useCallback` for checkpoint handlers to satisfy React hooks lint rules
- All progress update paths (`timeUpdate`, `videoEnded`, `markIncomplete`, checkpoints) now respect both circuit breakers
- Same-position circuit breaker: stops after 20 identical timestamps (handles "paused for 24h" case)
- Failure circuit breaker: stops after 10 consecutive failures
- Console hygiene: only operational warnings kept (breaker trips), per-request spam removed
- Code consistency: using captured `now` variable for timestamp instead of duplicate `Date.now()` calls
- 75 tests pass (18 LessonPlayerPage tests); lint clean

---

## 2026-05-06 — Ops: catalog TRUNCATE (keep users), schema applier, API stage refresh

### Completed

- [x] **RDS Query (dev + prod)** — Mutating `TRUNCATE enrollments, lessons, courses RESTART IDENTITY CASCADE` with `allow_mutating_sql` (runbook selective clear; `users` untouched; no `wipe_catalog`; no RDS snapshots).
- [x] **Schema applier** — Local [`scripts/deploy-rds-stack.sh`](scripts/deploy-rds-stack.sh) for **dev** and **prod** (uploads new `schema.sql` zip from repo `001`), then `aws lambda invoke` on **StreamMyCourse-RdsSchemaApplier-dev** / **prod** with `{}` → `{"ok": true}`.
- [x] **Read-back** — `lesson_progress` present in `information_schema` on both envs; catalog row counts zero except `users` (dev 5, prod 7).
- [x] **API Gateway** — `aws apigateway create-deployment` on **prod** (`hf8fcfj66g`, stage `prod`) and **dev** (`qstuxlbcp4`, stage `dev`); dev required `update-stage` patch to new `deploymentId` so public `GET …/progress` stopped returning `MissingAuthenticationTokenException` (now **401** without JWT, consistent with Cognito authorizer).
- [x] **Backend deploy** — [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) **dev** and **prod** with `COGNITO_USER_POOL_ARN` from respective Auth stacks (Lambda zip refresh; CF reported no template changes).

---

## 2026-05-06 — Agent tooling: `/commit` local HTTPS gate

### Completed

- [x] **Skills** — [`.cursor/skills/commit/SKILL.md`](.cursor/skills/commit/SKILL.md) and [`.cursor/skills/review-and-commit/SKILL.md`](.cursor/skills/review-and-commit/SKILL.md): when material changes warrant [`./scripts/run-local-integration-tests.sh`](scripts/run-local-integration-tests.sh), verify **`.env.local`** at the repo root defines **`LOCAL_COGNITO_PASSWORD`** (see **`.env.local.example`**) before running (no silent skip on missing credentials); narrow omit only for typo-only / non-runtime markdown paths per skill text.
- [x] **`AGENTS.md`** — “Before merging” aligned with that expectation (local HTTPS against dev).

---

## 2026-05-06 — Lesson progress UX and validation

### Completed

- [x] **`LessonProgressService._validate_position`** — When **`duration <= 0`** (unknown length on the client), skip **`duration + slack`** cap so updates are not rejected at ~30s; known duration behavior unchanged ([`services/progress/service.py`](infrastructure/lambda/catalog/services/progress/service.py), unit test in [`test_progress_service.py`](tests/unit/services/progress/test_progress_service.py)).
- [x] **Course detail** — Signed-in learners see per-lesson watch progress (bar under each lesson row): [`getCourseProgress`](frontend/src/lib/api.ts) + [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx); expected 503/403 cases ignored without noisy warnings.

---

## 2026-05-05 — RDS: lesson_progress DDL folded into 001_initial_schema

### Completed

- [x] **Schema** — Appended former `002_lesson_progress.sql` DDL to [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql); removed `002` so the schema-applier bundle (copy of `001` only) applies `lesson_progress` on deploy.
- [x] **Tests** — [`tests/unit/test_rds_schema_apply.py`](tests/unit/test_rds_schema_apply.py) asserts split/join of `001` includes `lesson_progress`, `idx_lesson_progress_course_user`, and `chk_lesson_progress_position_nonneg` (TDD red → green).

### Verification

- `python -m pytest tests/unit/test_rds_schema_apply.py -q`

### Operational follow-up (manual)

_Superseded by **2026-05-06 — Ops** above (schema applier invoked, RDS verified, API stages refreshed, `curl` returns 401 without JWT on `/progress`)._

---

## 2026-05-05 — Integration suite: CORS, lesson delete latency, scoped S3 cleanup

### Completed

- [x] **HTTP integration** — `INTEGRATION_EXPECTED_CORS_ORIGIN` (CI resolves first `CorsAllowOrigin` CSV segment in `deploy-backend.yml`; local runner can resolve from stack). OPTIONS CORS assertions use that value (`tests/integration/test_bootstrap_edges.py`).
- [x] **S3 integration** — Lesson delete test waits for async worker (`test_s3_cleanup.py`).
- [x] **Catalog** — Lesson delete enqueues media cleanup like course delete when the queue is configured (`services/course_management/service.py`); avoids API Gateway timeouts from synchronous S3 on the request path.
- [x] **Deploy scripts** — `deploy-backend.sh` / `deploy-media-cleanup.sh`: Python `zipfile` fallback when `zip(1)` is missing (Git Bash on Windows); `validate-template` uses `cygpath -m` for media-cleanup on MSYS.
- [x] **Session safety net** — `tests/integration/helpers/cleanup.py`: S3 deletes only under `{courseId}/` for courses whose titles matched `integration-test-` on that sweep (no full dev bucket wipe). `log_integration_cleanup_error` logs at ERROR and emits GitHub `::error::` when cleanup is skipped or fails, so CI surfaces it without failing pytest.
- [x] **Docs / operator hints** — `AGENTS.md` links `scripts/run-local-integration-tests.sh`; added `.env.local.example` for local Cognito env.

---

## 2026-05-05 — DynamoDB Catalog Fully Removed (RDS-Only)

### Completed

- [x] **Infrastructure** — Removed `CatalogTable` from `api-stack.yaml`; RDS is now the only persistence path
- [x] **Parameters** — Removed `UseRds` parameter and `USE_RDS` env var from Lambda
- [x] **Repositories** — Deleted DynamoDB repo implementations (`services/*/repo.py`); only `rds_repo.py` implementations remain
- [x] **Bootstrap** — Catalog Lambda now requires `RdsStackName` (RDS stack must exist); returns 503 `catalog_unconfigured` when unavailable
- [x] **Deploy script** — Added pre-flight validation for RDS stack existence in `deploy-backend.sh`
- [x] **Tests** — Added progress endpoint 503 test; added dev backend job contract test
- [x] **Code quality** — Removed dangerous `assert progress_service is not None` from production handler

### Operational Note

Existing stacks may have orphaned DynamoDB tables from previous deployments (retained by `DeletionPolicy: Retain`). After confirming RDS migration is stable, manually delete these tables in the AWS console:
- `StreamMyCourse-Catalog-dev`
- `StreamMyCourse-Catalog-prod`

---

## 2026-05-05 — Lesson Progress Tracking (RDS)

### Completed

- [x] **Database** — `lesson_progress` in [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) — FKs to users, lessons, courses; index on (course_id, user_sub); previously shipped as `002_lesson_progress.sql` until folded into `001` (see Implementation History entry **RDS: lesson_progress DDL folded into 001_initial_schema**).
- [x] **Backend Service** — `services/progress/` bounded context:
  - `ports.py` — Repository protocol
  - `contracts.py` — API DTOs
  - `service.py` — Business logic (authorization, auto-complete at 92%, position validation)
  - `rds_repo.py` — PostgreSQL adapter with ON CONFLICT UPDATE
  - `controller.py` — HTTP routing for GET/PUT endpoints
- [x] **Wiring** — `config.py`, `bootstrap.py`, `index.py` — Progress service integrated as optional 4th tuple member in AwsDeps
- [x] **Infrastructure** — `api-stack.yaml` — CloudFormation resources for endpoints, Lambda env vars
- [x] **Frontend** — `api.ts` types/functions, `LessonPlayerPage.tsx` integration with progress bar, completion badges, resume position
- [x] **Tests** — 37 backend unit tests, 19 frontend tests (68 total), all passing
- [x] **Documentation** — ADR-0010, module-map.md update

### Technical Notes

- RDS-only: Returns 503 `progress_requires_rds` when USE_RDS=false
- Authorization: enrollment OR course ownership required
- Auto-complete: position/duration >= PROGRESS_COMPLETE_RATIO (default 0.92)
- Position slack: allows up to 30 seconds past video duration
- No throttling in MVP (deferred)

### Verification

- All CI checks pass (vulture, boundary checks, lint, knip, build, test)
- CloudFormation template parses successfully

---

## 2026-05-05 — SQS Interface VPC Endpoint for Catalog Lambda

### Problem
Catalog Lambda running in private subnets (via RDS stack VPC config) could not reach SQS to send media cleanup messages. The VPC had Interface endpoints for Secrets Manager and CloudWatch Logs, plus Gateway endpoints for S3 and DynamoDB, but **SQS does not support Gateway endpoints** (only Interface). Without a NAT Gateway, there was no route from the private subnet to `sqs.eu-west-1.amazonaws.com`.

### Solution
Added `SqsEndpoint` Interface VPC endpoint to [`infrastructure/templates/rds-stack.yaml`](infrastructure/templates/rds-stack.yaml) following the existing pattern for Secrets Manager and CloudWatch Logs endpoints:
- Type: `AWS::EC2::VPCEndpoint` with `VpcEndpointType: Interface`
- `PrivateDnsEnabled: true` so the Lambda SDK uses standard SQS hostnames
- Attached to `PrivateSubnet` and `EndpointSecurityGroup` (existing security group already allows ingress from Lambda SG on 443)

### Verification
- CloudFormation template validation: `YAML_OK`
- After CI/CD deploy to dev/prod: Catalog Lambda can successfully `sqs:SendMessage` to the media cleanup queue
- Media cleanup worker receives and processes deletion messages

### Cost Impact
~$7.20/month per environment (same as existing Secrets Manager and Logs endpoints); significantly cheaper than NAT Gateway (~$32+/month).

---

## 2026-05-04 — CloudFormation DeletionPolicy audit and S3 data-loss fix

### Incident

Investigation of recurring "all S3 data deleted on deploy" reports identified the **VideoBucket** in [`infrastructure/templates/video-stack.yaml`](infrastructure/templates/video-stack.yaml) as **lacking `DeletionPolicy`/`UpdateReplacePolicy: Retain`**. Any CloudFormation operation that requires bucket replacement (certain property changes), or a stack delete, would destroy the bucket and **all uploaded course/lesson media** — with **no versioning** to recover from. The `CatalogTable` (DynamoDB) and `DbInstance` (RDS) were already protected (`Retain` and `Snapshot` respectively); the audit found four other unprotected resources that warranted the same hardening.

### Completed

- [x] **Video bucket (CRITICAL)** — [`infrastructure/templates/video-stack.yaml`](infrastructure/templates/video-stack.yaml) — `VideoBucket` now has `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain`. Prevents bucket and media destruction on stack delete or property-driven replacement.
- [x] **SPA hosting buckets (MEDIUM)** — [`infrastructure/templates/edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml) — `SiteBucket` and `TeacherSiteBucket` retain on delete/replace. Contents are rebuildable from source, but retention prevents service downtime while CloudFront origin churns.
- [x] **Async cleanup queues (LOW)** — [`infrastructure/templates/media-cleanup-stack.yaml`](infrastructure/templates/media-cleanup-stack.yaml) — `MediaCleanupQueue` and `MediaCleanupDlq` retain on delete so in-flight cleanup jobs and forensic DLQ messages survive a stack teardown.
- [x] **Billing alerts (LOW)** — [`infrastructure/templates/billing-alarm.yaml`](infrastructure/templates/billing-alarm.yaml) — `BillingAlertTopic` retains on delete to preserve email subscriptions and operator pager wiring.

### Verification

- `aws cloudformation validate-template` passes for all four modified templates (`video-stack.yaml`, `edge-hosting-stack.yaml`, `media-cleanup-stack.yaml`, `billing-alarm.yaml`).
- `cfn-lint` passes for all modified templates (`./scripts/cfn-lint-templates.sh`).
- No existing data needs migration — `Retain` policies are inert until a delete/replace event.

### Ops / Rollout

- Next deploy via [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) / [`scripts/deploy-edge.sh`](scripts/deploy-edge.sh) attaches the new policies to the live stacks (no resource replacement; CFN treats DeletionPolicy as metadata).
- Existing dev/prod video buckets continue to hold their data; the new policies guard them against the next incident.
- **Convention going forward:** any new `AWS::S3::Bucket`, `AWS::DynamoDB::Table`, `AWS::RDS::DBInstance`, `AWS::SQS::Queue`, or `AWS::SNS::Topic` resource MUST set `DeletionPolicy: Retain` (or `Snapshot` for RDS) unless it provably holds only ephemeral state.

---

## 2026-05-04 — iOS Safari video playback fix

### Completed

- [x] **Lesson Player** — [`frontend/src/pages/LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx) — Added `preload="metadata"` and `crossOrigin="anonymous"` to the video element to fix iOS Safari playback (muted speaker icon / black screen). iOS Safari requires explicit preload metadata and CORS handling for cross-origin video sources (S3/CloudFront presigned URLs).

---

## 2026-05-05 — Deploy workflow OIDC uses repository Actions variable for role ARN

### Completed

- [x] **GitHub Actions** — [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — `configure-aws-credentials` `role-to-assume` and reusable-workflow `AWS_DEPLOY_ROLE_ARN` inputs now use **`${{ vars.AWS_DEPLOY_ROLE_ARN }}`** (not **`secrets.AWS_DEPLOY_ROLE_ARN`**), aligned with [`AGENTS.md`](AGENTS.md) and the **verify-rds** callers. Jobs that need Cognito secrets still use **`environment: dev`**, while **`resolve-oidc-deploy-role`** pins the backend OIDC role from the **repository** variable so Environment-scoped secrets cannot shadow **`AWS_DEPLOY_ROLE_ARN`** with a web-only role (same **`sqs:CreateQueue` AccessDenied** symptom when misconfigured).
- [x] **Contract test** — [`tests/unit/test_deploy_backend_workflow_contract.py`](tests/unit/test_deploy_backend_workflow_contract.py) — asserts the workflow contains no `secrets.AWS_DEPLOY_ROLE_ARN` and that **`integration-http-tests`** assumes the role output from **`resolve-oidc-deploy-role`**.

### Ops

- **Repository → Settings → Secrets and variables → Actions → Variables:** set **`AWS_DEPLOY_ROLE_ARN`** to the IAM role ARN that carries **backend** deploy permissions ([`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) on the OIDC role, or the unified stack output). Re-run **Deploy** after merge if the failed media-cleanup stack left **`ROLLBACK_COMPLETE`**; delete that stack in CloudFormation before retry if a clean create is required.

---

## 2026-05-04 — Async S3 media cleanup (SQS + worker) for course delete

### Completed

- [x] **SQS client** — [`infrastructure/lambda/catalog/services/common/sqs_client.py`](infrastructure/lambda/catalog/services/common/sqs_client.py) — `send_media_cleanup_job` (JSON payload `courseId` / `keys` / `timestamp`; splits messages if body would exceed SQS size; **propagates** SQS API errors; on a failed chunk after earlier sends succeed, logs `media_cleanup_sqs_partial_send` with chunk index, `course_id`, and a truncated queue URL prefix, then re-raises; empty queue URL with non-empty keys raises `BadRequest`; oversized single key raises `BadRequest`).
- [x] **Catalog service** — [`infrastructure/lambda/catalog/services/course_management/service.py`](infrastructure/lambda/catalog/services/course_management/service.py) — If the course has deduplicated media keys and `MEDIA_CLEANUP_QUEUE_URL` is empty, **`ServiceUnavailable` (503) before** `delete_course_and_lessons` (no partial DB delete on misconfiguration). After DB delete, enqueues when keys exist and the queue is configured (no synchronous `_delete_media_keys` fallback for course delete). Other code paths (e.g. lesson delete) still use `_delete_media_keys` where applicable.
- [x] **Errors** — [`infrastructure/lambda/catalog/services/common/errors.py`](infrastructure/lambda/catalog/services/common/errors.py) — `ServiceUnavailable` for misconfigured queue on course delete with media.
- [x] **Config / bootstrap** — [`infrastructure/lambda/catalog/config.py`](infrastructure/lambda/catalog/config.py), [`infrastructure/lambda/catalog/bootstrap.py`](infrastructure/lambda/catalog/bootstrap.py) — `MEDIA_CLEANUP_QUEUE_URL` env wiring.
- [x] **Worker Lambda** — [`infrastructure/lambda/media_cleanup/worker.py`](infrastructure/lambda/media_cleanup/worker.py) — SQS batch handler, `delete_objects` in chunks of 1000, `ReportBatchItemFailures` on errors; if `VIDEO_BUCKET` is unset, returns **per-record** `batchItemFailures` for every `messageId` so messages are not silently acknowledged.
- [x] **CloudFormation** — [`infrastructure/templates/media-cleanup-stack.yaml`](infrastructure/templates/media-cleanup-stack.yaml); **API stack** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — optional `MediaCleanupQueueUrl` / `MediaCleanupQueueArn` + `sqs:SendMessage` when ARN set + `MEDIA_CLEANUP_QUEUE_URL` on catalog Lambda.
- [x] **Deploy** — [`scripts/deploy-media-cleanup.sh`](scripts/deploy-media-cleanup.sh); [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) — deploys media-cleanup stack after the video stack for **dev** and **prod**, then passes queue URL/ARN into the API deploy.
- [x] **Tests** — [`tests/unit/test_sqs_client.py`](tests/unit/test_sqs_client.py), [`tests/unit/test_media_cleanup.py`](tests/unit/test_media_cleanup.py), service tests in [`tests/unit/services/course_management/test_service.py`](tests/unit/services/course_management/test_service.py); [`tests/unit/test_config.py`](tests/unit/test_config.py) for `MEDIA_CLEANUP_QUEUE_URL`; [`tests/integration/test_s3_cleanup.py`](tests/integration/test_s3_cleanup.py) polls S3 until async cleanup removes the object after course delete.
- [x] **CI** — [`.github/workflows/ci.yml`](.github/workflows/ci.yml) parses `media-cleanup-stack.yaml`; [`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py) allows boto3 in `sqs_client.py`.
- [x] **Docs** — [`design.md`](design.md) §10 backend note; [`plans/architecture/module-map.md`](plans/architecture/module-map.md) lists `sqs_client.py`.

### Ops / IAM

- **GitHub deploy role:** [`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) — **`SqsStreamMyCourseQueues`** plus **`lambda:*`** on both **`function:StreamMyCourse-*`** and **`event-source-mapping:*`** (SQS + worker deploy). [`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) mirrors the same statements with **`!Sub`**. JSON files keep **`YOUR_AWS_ACCOUNT_ID`**; [`scripts/apply-github-deploy-role-policies.sh`](scripts/apply-github-deploy-role-policies.sh) / [`.ps1`](scripts/apply-github-deploy-role-policies.ps1) substitute it from **`sts get-caller-identity`** before **`put-role-policy`**. Sync the live role or redeploy the IAM stack if deploy fails with SQS/Lambda mapping access denied.
- **Manual verification:** Deploy via pipeline or `./scripts/deploy-backend.sh <dev|prod>`; delete a course with uploaded media; API returns 200 only after enqueue succeeds; S3 objects disappear once the worker runs. **Rollback:** redeploy a catalog build that restores prior behavior, or fix queue permissions / worker; there is **no** silent sync-delete fallback for course delete when keys exist.

---

## 2026-05-05 — RDS enrollments FK: ON DELETE CASCADE with course delete

### Completed

- [x] **Schema** — [`infrastructure/database/migrations/001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) — `enrollments.course_id` references `courses(id) ON DELETE CASCADE` (same idea as `lessons.course_id`).
- [x] **Catalog RDS repo** — [`infrastructure/lambda/catalog/services/course_management/rds_repo.py`](infrastructure/lambda/catalog/services/course_management/rds_repo.py) — `delete_course_and_lessons` uses a single `DELETE FROM courses`; enrollments and lessons are removed by FK cascade.
- [x] **Tests** — [`tests/unit/test_rds_repos.py`](tests/unit/test_rds_repos.py) — `test_delete_course_and_lessons_single_transaction` asserts no separate `DELETE FROM enrollments` SQL.

### Ops

- **Existing** dev/prod RDS: upgrade `enrollments_course_id_fkey` with mutating SQL via **`StreamMyCourse-RdsQuery-<env>`** (see [`RDS_QUERY_RUNBOOK.md`](infrastructure/database/RDS_QUERY_RUNBOOK.md)) — `DROP CONSTRAINT IF EXISTS` then `ADD CONSTRAINT … ON DELETE CASCADE`; `CREATE TABLE IF NOT EXISTS` in `001` does not alter an already-created table.
- Redeploy **catalog** Lambda after merge so deployed code matches repo.

---

## 2026-05-05 — Public catalog reads: course detail + lesson list (remove `/preview`)

### Completed

- [x] **Service** — [`infrastructure/lambda/catalog/services/course_management/service.py`](infrastructure/lambda/catalog/services/course_management/service.py) — Added **`list_lessons_public`** (gate-before-query: `get_course` then DRAFT visibility via `_can_manage_course_unenrolled` before `repo.list_lessons`). Removed **`get_course_preview`**. Existing **`get_course_detail_with_enrollment`** already sets **`enrolled=false`** for anonymous callers on **PUBLISHED** courses.
- [x] **Controller** — [`infrastructure/lambda/catalog/services/course_management/controller.py`](infrastructure/lambda/catalog/services/course_management/controller.py) — **`GET /courses/{id}`** and **`GET /courses/{id}/lessons`** no longer call **`_require_authenticated`** or **`ensure_can_view_lessons_and_playback`**; lessons use **`list_lessons_public`**. **`GET /playback/...`** unchanged (still authenticated + enrollment when enforced). Removed **`/preview`** route and handler.
- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — Removed **`/courses/{courseId}/preview`** resource and methods; **`GET /courses/{courseId}`** and **`GET /courses/{courseId}/lessons`** use **`AuthorizationType: NONE`**; deployment logical id **`CatalogApiDeploymentV8` → `CatalogApiDeploymentV9`** (stage **`DeploymentId`** updated; **`DependsOn`** no longer references preview methods).
- [x] **Frontend** — [`frontend/src/lib/api.ts`](frontend/src/lib/api.ts) — Removed **`getCoursePreview`** / **`lessonPreviewsToStubLessons`**. [`CourseDetailPage.tsx`](frontend/src/pages/CourseDetailPage.tsx) / [`LessonPlayerPage.tsx`](frontend/src/pages/LessonPlayerPage.tsx) always use **`getCourse` + `listLessons`**; **`previewOnly`** = not signed in, **`needsEnrollment`** = signed in and **`enrolled === false`**; playback enrollment errors load sidebar from **`listLessons`** (thumbnails visible).
- [x] **Tests** — [`tests/unit/services/course_management/test_service.py`](tests/unit/services/course_management/test_service.py), [`test_controller.py`](tests/unit/services/course_management/test_controller.py); [`tests/integration/test_publish.py`](tests/integration/test_publish.py) (anonymous **`httpx.Client`** without `Authorization`); [`frontend/src/lib/api.test.ts`](frontend/src/lib/api.test.ts); removed **`get_course_preview`** from [`tests/integration/helpers/api.py`](tests/integration/helpers/api.py).
- [x] **Docs** — [`design.md`](design.md) §7 API + §9 security + §10 deployment note (**`CatalogApiDeploymentV9`**).

### Ops

- **Deploy backend** after merge so API Gateway stage picks up **`CatalogApiDeploymentV9`** (otherwise anonymous **`GET /courses/.../lessons`** can still return **403 Missing Authentication Token** from a stale stage snapshot). Smoke: anonymous `curl` to **`/courses/{published-id}`** and **`/lessons`** without **`Authorization`** → **200**; DRAFT id → **404**; **`/preview`** path removed at gateway (404 from API GW or Lambda **`not_found`**).

---

## 2026-05-04 — Lesson video upload: second presign no longer deletes prior S3 object

### Completed

- [x] **`get_upload_url` behavior** — [`infrastructure/lambda/catalog/services/course_management/service.py`](infrastructure/lambda/catalog/services/course_management/service.py) — After a successful conditional DB update to a new lesson `videoKey`, the service **no longer** deletes the previous S3 key on presign. A second presign could race with a client still `PUT`ting the first URL, which made the first object disappear while the DB pointed at the new key.
- [x] **Conflict path unchanged** — On `Conflict` from `set_lesson_video_if_video_key_matches`, the service still deletes **only** the newly presigned key (unused by DB) and re-raises.
- [x] **Tests** — [`tests/unit/services/course_management/test_service.py`](tests/unit/services/course_management/test_service.py) — `test_second_presign_does_not_delete_previous_video_key_in_s3`; `test_conflict_deletes_only_new_presigned_key_not_previous`.

### Tradeoffs / ops

- **Orphan objects:** Abandoned lesson-video keys under `{courseId}/lessons/{lessonId}/video/` may remain in the private bucket until a future lifecycle rule or sweeper; accepted for MVP.
- **Rollback:** Reverting the service commit restores eager deletion of the prior key (only if that tradeoff is preferable operationally).

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

## 2026-05-05 — RDS Query runbook: selective catalog clear, ops learnings, users policy

### Completed

- [x] **Runbook** — [`infrastructure/database/RDS_QUERY_RUNBOOK.md`](infrastructure/database/RDS_QUERY_RUNBOOK.md) — Section for clearing `enrollments` / `lessons` / `courses` while keeping `users`; verifying `AllowMutatingSql`; `TRUNCATE` vs `DELETE` fallback on statement timeout; `aws lambda invoke --cli-read-timeout`; timestamp casts for read-backs; tighten note to disable **`ALLOW_MUTATING_SQL`** after maintenance alongside catalog wipe.
- [x] **Policy** — Same runbook: **Policy: `users` table`** — assistants and operators must not delete or truncate `users` (including via `wipe_catalog`); refuse chat-driven user deletion and route legal erasure outside ad-hoc RDS Query.
- [x] **Cursor skill** — [`.cursor/skills/query-rds/SKILL.md`](.cursor/skills/query-rds/SKILL.md) — Agent bullet mirroring the users-table refusal for `/query_rds`.

---

## 2026-05-04 — Pre-public release: Security hardening and professional README

### Completed

- [x] **Professional README** — [`README.md`](README.md) — Complete rewrite transforming internal-facing documentation into product-focused presentation; includes architecture mermaid diagram, feature overview for students/instructors, tech stack table, quick start guide, and security section with proprietary notice.
- [x] **Security hardening — IAM policy JSON sanitization** — [`infrastructure/iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json), [`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json), [`infrastructure/iam-trust-github-oidc.json`](infrastructure/iam-trust-github-oidc.json) — Replaced hardcoded AWS account id with **`YOUR_AWS_ACCOUNT_ID`** placeholder in IAM policy files; [`scripts/apply-github-deploy-role-policies.sh`](scripts/apply-github-deploy-role-policies.sh) / [`.ps1`](scripts/apply-github-deploy-role-policies.ps1) substitute it from `sts get-caller-identity` before `put-role-policy`.
- [x] **Security hardening — GitHub variable setup** — Set `AWS_ACCOUNT_ID` GitHub Actions variable on **dev** and **prod** environments via `/use-cli` (AWS) and `/github-cli` (GitHub CLI); same value used for both environments.
- [x] **Security hardening — ImplementationHistory sanitization** — Redacted specific AWS resource identifiers (CloudFront domain, distribution ID, S3 bucket names, account ID references) from historical entries while preserving engineering narrative.
- [x] **Security policy** — [`SECURITY.md`](SECURITY.md) — Created security policy document with vulnerability reporting guidelines, supported versions table, AWS account ID placeholder instructions, and security best practices for operators.

### Ops

- When deploying IAM policies from the JSON files, operators run [`scripts/apply-github-deploy-role-policies.sh`](scripts/apply-github-deploy-role-policies.sh) / [`.ps1`](scripts/apply-github-deploy-role-policies.ps1) (substitutes **`YOUR_AWS_ACCOUNT_ID`**) or replace that placeholder manually before upload.
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
- CI/CD [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) progressed through backend deploy phases for non-prod then prod stacks (historical ordering — see live workflow **`needs`** graph)
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
- [x] **Integration cleanup** — [`tests/integration/helpers/cleanup.py`](tests/integration/helpers/cleanup.py) — session safety net empties the **whole** configured non-prod video bucket (not only legacy `uploads/` prefixes).

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
- [x] **API Gateway** — [`infrastructure/templates/api-stack.yaml`](infrastructure/templates/api-stack.yaml) — resource `/courses/mine`, `GET` + `OPTIONS`, Cognito authorizer wiring; deployment logical id **CatalogApiDeploymentV8** (bump so stage picks up new methods).
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
3. (Legacy) DynamoDB migration is complete; no `migrate-dynamodb-to-rds.py` step remains.
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
- [x] **Deploy pipeline (dev)** — [`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml) — three RDS-focused jobs added alongside existing backend + HTTPS pytest gates:
  - **`deploy-rds-dev`** — builds a **schema-applier** zip (`infrastructure/lambda/rds_schema_apply/index.py` + vendored **`psycopg2-binary`** + copied **`001_initial_schema.sql`** as `schema.sql`), uploads to **`streammycourse-artifacts-<account>-<region>`**, then `aws cloudformation deploy` for `StreamMyCourse-Rds-dev` with **`SchemaApplierCodeS3Bucket`** / **`SchemaApplierCodeS3Key`**, then `aws rds wait db-instance-available` on `streammycourse-dev`.
  - **`apply-schema-dev`** — resolves **`SchemaApplierFunctionName`** from stack outputs and runs **`aws lambda invoke`** (payload `{}`); the Lambda runs in the **private subnet** with the catalog **Lambda SG**, reads **`SECRET_ARN`** from env, fetches JSON from Secrets Manager, and executes the bundled DDL with **`psycopg2`** + **`sslmode=require`** (no credentials on the GitHub runner, no TCP 5432 from the runner).
  - **`verify-dev-rds`** — calls **`verify-rds-reusable.yml`** with **`github_environment: dev`** and dev stack inputs; exports **`INTEGRATION_*`** pytest env vars + **`INTEGRATION_COGNITO_JWT`**, then runs **`test_rds_path.py`**.
- [x] **Dev backend wiring** — [`deploy-backend-dev`](.github/workflows/deploy-backend.yml) job now sets **`RDS_STACK_NAME=StreamMyCourse-Rds-dev`** + **`USE_RDS=true`** as job-level env vars and depends on `deploy-rds-dev` + `apply-schema-dev`. [`scripts/deploy-backend.sh`](scripts/deploy-backend.sh) already forwards both to `aws cloudformation deploy` as `RdsStackName` / `UseRds` parameter overrides (no script change needed).
- [x] **Integration smoke tests** — [`tests/integration/test_rds_path.py`](tests/integration/test_rds_path.py) — catalog smoke using the existing `api` / `course_factory` / `lesson_factory` fixtures (POST/GET round-trip, PUT persistence, lesson FK).

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
- [x] **Data migration tool (legacy, removed)** — `scripts/migrate-dynamodb-to-rds.py` — one-shot idempotent DynamoDB → RDS copy used during cutover; deleted after migration completion.
- [x] **IAM (GitHub deploy role)** — [`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) + [`infrastructure/templates/github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) — added **`RdsStackManage`**, **`Ec2VpcStackManage`**, **`SecretsManagerRdsCredentials`**, **`SecretsManagerRotationAndList`** statements so CI can deploy `StreamMyCourse-Rds-*`.
- [x] **Boundary check** — [`scripts/check_lambda_boundaries.py`](scripts/check_lambda_boundaries.py) — `bootstrap.py` added to `allowed_boto3_files`; new `allowed_psycopg2_files` (`bootstrap.py` + the three `rds_repo.py`); HTTP-import guard extended to all `rds_repo.py`. CI parity: **28 files pass**.
- [x] **Tests (TDD)** — [`tests/unit/test_config.py`](tests/unit/test_config.py) (new `TestRdsFields`), [`tests/unit/test_rds_repos.py`](tests/unit/test_rds_repos.py) (54 assertions across the three RDS adapters with a `FakeCursor`/`FakeConn` driver mock), [`tests/unit/test_bootstrap.py`](tests/unit/test_bootstrap.py) (`TestBuildAwsDepsWithRds` + `TestRdsConnectionFactory` covering Secrets Manager failure modes and `sslmode=require`). Full suite: **311 passed**, **vulture min-confidence 61 clean**.
- [x] **Docs** — new ADR [`plans/architecture/adr-0008-dynamodb-to-rds-migration.md`](plans/architecture/adr-0008-dynamodb-to-rds-migration.md); [`plans/architecture/module-map.md`](plans/architecture/module-map.md) updated for the new adapters + psycopg2/boto3 boundaries; [`tests/integration/README.md`](tests/integration/README.md) gained an **RDS cutover runbook** (deploy `rds-stack` → apply schema → run migrator dry-run/live → redeploy api stack with `UseRds=true` → HTTPS integration suite → rollback by flipping `UseRds=false` and redeploying).

### Decisions (see [ADR-0008](plans/architecture/adr-0008-dynamodb-to-rds-migration.md))

- **RDS** on `db.t4g.micro` (free-tier friendly) over Aurora Serverless v2 (no scale-to-zero, pricier minimum).
- **Lambda in VPC** with Gateway endpoints for S3/DynamoDB so DynamoDB repos keep working during rollback with no NAT cost.
- **Direct psycopg2** (no SQLAlchemy) — matches the thin-adapter style of the existing DynamoDB repos.
- **Feature flag `USE_RDS` off by default** — ports/contracts unchanged, rollback is a parameter flip + one `deploy.ps1 -Template api` redeploy.
- **Phase 2 groundwork, not a cost-down move.** DynamoDB is fine for MVP; RDS unlocks relational dashboards, payments/enrollments reporting, and richer joins planned in [`roadmap.md`](./roadmap.md) Phase 2.

### Deferred to operator (post-code-merge)

- Deploy `StreamMyCourse-Rds-<env>` stack; apply [`001_initial_schema.sql`](infrastructure/database/migrations/001_initial_schema.sql) via bastion/psql; flip `UseRds=true` on `StreamMyCourse-Api-<env>` when ready. Runbook: [`tests/integration/README.md`](tests/integration/README.md).

---

## 2026-05-03 — Security hardening (infra, IAM, CI, HTTPS integration smoke)

### Completed

- [x] **CloudFront response headers** — [`infrastructure/templates/edge-hosting-stack.yaml`](infrastructure/templates/edge-hosting-stack.yaml) — **`SpaSecurityHeadersPolicy`** (HSTS, **`nosniff`**, **`DENY`** frame options, referrer policy) attached to student + teacher default cache behaviors.
- [x] **GitHub Actions** — [`deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml) / [`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml) declare **`workflow_call.secrets`**; [`deploy-backend.yml`](.github/workflows/deploy-backend.yml) passes explicit **`secrets:`** maps (no **`secrets: inherit`** on those calls).
- [x] **GitHub deploy role (backend policy)** — [`github-deploy-role-stack.yaml`](infrastructure/templates/github-deploy-role-stack.yaml) + [`iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json) — CloudFormation scoped to **`StreamMyCourse-*`** stacks (eu-west-1 + us-east-1) with **`ValidateTemplate`** / **`ListStacks`** on **`*`**; Lambda / DynamoDB / log groups scoped to **`StreamMyCourse-*`**; API Gateway + Cognito remain regional with conditions where applicable; S3 still account-scoped for artifact + dynamic bucket names.
- [x] **Dev env docs** — [`frontend/.env.example`](frontend/.env.example) — **`VITE_API_PROXY_TARGET`** documented as required for Vite dev when using **`/api`** proxy.
- [x] **Tests** — [`tests/unit/services/course_management/test_service.py`](tests/unit/services/course_management/test_service.py) (**`set_lesson_video_if_video_key_matches`**), [`test_storage.py`](tests/unit/services/course_management/test_storage.py) (sanitized filenames); [`tests/integration/test_playback_upload.py`](tests/integration/test_playback_upload.py) (**invalid video / image content types** → **400**).
- [x] **Follow-up (presign + Gateway CORS)** — [`storage.py`](infrastructure/lambda/catalog/services/course_management/storage.py): removed invalid **`Conditions=`** kwargs from **`generate_presigned_url`** (boto3 does not support them; caused **500** on **`POST /upload-url`** against deployed stacks). [`test_bootstrap_edges.py`](tests/integration/test_bootstrap_edges.py): OPTIONS / GatewayResponse expectations aligned with explicit **`GatewayResponseAllowOrigin`** (**`http://localhost:5173`**).

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
- [x] **[`.github/workflows/deploy-backend.yml`](.github/workflows/deploy-backend.yml)** — **`deploy-edge-*`** job graph; edge steps run unified script. Dev **`deploy-backend-*`** gates on **`deploy-edge-dev`** (plus RDS/schema); student/teacher SPA jobs gate on **`integration-http-tests`** among other **`needs`** (see live YAML); **prod** app jobs **`needs`** **`deploy-edge-prod`** and the full predecessor graph; **auth** fail-fast if **`COGNITO_DOMAIN_PREFIX`** unset.
- [x] **[`.github/workflows/deploy-web-reusable.yml`](.github/workflows/deploy-web-reusable.yml)** / **[`deploy-teacher-web-reusable.yml`](.github/workflows/deploy-teacher-web-reusable.yml)** — **`AWS_REGION: us-east-1`**; stack **`StreamMyCourse-EdgeHosting-${env}`**; outputs **`StudentBucketName`**, **`StudentDistributionId`**, **`StudentSiteUrl`** / teacher equivalents.
- [x] **[`infrastructure/iam-policy-github-deploy-web.json`](infrastructure/iam-policy-github-deploy-web.json)** — **`DescribeStacks`** ARNs for **`StreamMyCourse-EdgeHosting-*`** (**`us-east-1`**).
- [x] **[`infrastructure/iam-policy-github-deploy-backend.json`](infrastructure/iam-policy-github-deploy-backend.json)** — *(unchanged this session; already had ACM / Route53 / CloudFront for edge.)*
- [x] **[`infrastructure/deploy.ps1`](infrastructure/deploy.ps1)** — **`-Template edge-hosting`**, **`TeacherDomainName`**, optional **`CertPrimaryDomain`**.
- [x] **[`.github/workflows/ci.yml`](.github/workflows/ci.yml)** — Parse **`edge-hosting-stack.yaml`**; **`workflow-lint`** unchanged.
- [x] **[`tests/unit/test_deploy_edge_script.py`](tests/unit/test_deploy_edge_script.py)** — **`bash -n`** + single-stack **`us-east-1`** contract.
- [x] Docs: [`infrastructure/docs/edge-hosting-migration.md`](infrastructure/docs/edge-hosting-migration.md), [`plans/architecture/adr-0007-web-hosting.md`](plans/architecture/adr-0007-web-hosting.md) addendum, [`design.md`](design.md), [`roadmap.md`](roadmap.md), [`AGENTS.md`](AGENTS.md), [`infrastructure/README.md`](infrastructure/README.md), [`admin-auth-runbook.md`](infrastructure/docs/admin-auth-runbook.md).
- [x] **Prod app deploy gate** — **`deploy-backend-prod`**, **`deploy-web-prod`**, **`deploy-teacher-web-prod`** **`needs`** **`integration-http-tests`** (HTTPS pytest gate), **`verify-dev-rds`**, **`deploy-edge-dev`**, **`deploy-backend-dev`**, **`deploy-web-dev`**, **`deploy-teacher-web-dev`**, **`deploy-edge-prod`**, and related RDS predecessors so prod never ships early. (**Historical note:** predecessor pipelines sometimes modeled an extra standalone backend deploy stage before SPA work.)
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
- [x] Added PowerShell runner [`scripts/run-integration-tests.ps1`](scripts/run-integration-tests.ps1) to deploy **dev**/**prod** backends, export **`INTEGRATION_*`** pytest env vars, and run `python -m pytest tests/integration`.
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

### Third-backend integration experiment (removed)
- Historical note: StreamMyCourse briefly modeled a dedicated extra backend stack deployed before dev/prod SPA work so HTTPS pytest could target it. **Managed CI now targets dev stacks only** (`streammycourse-api`, `StreamMyCourse-Video-dev`, RDS-backed catalog); integration pytest env vars live under **`INTEGRATION_*`**; see [`tests/integration/README.md`](tests/integration/README.md) + **`.github/workflows/deploy-backend.yml`**.

### Test harness (HTTP via httpx + pytest)
- [x] **Layout:** [`tests/integration/`](tests/integration/) at repo root (outside the Lambda zip; not scanned by `check_lambda_boundaries.py` or vulture).
- [x] **Fixtures** in [`conftest.py`](tests/integration/conftest.py): `api_base_url`, `http_client`, `api`, `course_factory`, `lesson_factory`. Course teardown deletes via `DELETE /courses/{id}`; lesson cleanup is implicit (course delete cascades).
- [x] **Helpers:** [`api.py`](tests/integration/helpers/api.py) (typed httpx wrapper per endpoint), [`factories.py`](tests/integration/helpers/factories.py) (UUID-prefixed titles), [`cleanup.py`](tests/integration/helpers/cleanup.py) (HTTPS `GET /courses/mine` + `DELETE` for prefixed titles, plus dev-only S3 sweep).
- [x] **Session-end safety net:** `pytest_sessionfinish` calls [`cleanup.run_safety_net`](tests/integration/helpers/cleanup.py) — API course cleanup when `INTEGRATION_API_BASE_URL` and `INTEGRATION_COGNITO_JWT` are set, then empties the allowed **dev** video bucket pattern via boto3; logs to `$GITHUB_STEP_SUMMARY` but **never fails** the job.

### Test scenarios (28 collected)
- [x] **Smoke** ([`test_smoke.py`](tests/integration/test_smoke.py)) — harness wiring + cleanup proof.
- [x] **S1 edges** ([`test_bootstrap_edges.py`](tests/integration/test_bootstrap_edges.py)) — OPTIONS preflight, origin echo, 404 unknown route/method, 400 malformed JSON / array body, 400 missing required `courseId`/`lessonId` on `/upload-url`.
- [x] **S2 courses** ([`test_courses.py`](tests/integration/test_courses.py)) — CRUD + draft-not-in-public-catalog filter + delete cascades to lessons.
- [x] **S3 publish** ([`test_publish.py`](tests/integration/test_publish.py)) — publish-without-ready-lesson 400, video-ready-without-upload 400, full publish flow appears in catalog.
- [x] **S4 playback / upload** ([`test_playback_upload.py`](tests/integration/test_playback_upload.py)) — playback gating, presigned URL shape, full S3 round-trip (`@pytest.mark.slow`) verifying PUT then GET via presigned URLs.
- [x] **S5 lesson ordering regression** ([`test_lesson_ordering.py`](tests/integration/test_lesson_ordering.py)) — delete-middle-then-create no longer collides; `list_lessons` returns sorted by `order`.

### Static-check coverage in PR/push CI
- [x] [`/.github/workflows/ci.yml`](.github/workflows/ci.yml): new `integration-tests-static` job — installs test deps, py-compiles `tests/integration/**/*.py`, and runs `pytest --collect-only` to surface import errors before they hit a real deploy. `cloudformation` job now also parses `video-stack.yaml`.

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

*Last updated: 2026-05-16 (question bank names docs + final verification)*
