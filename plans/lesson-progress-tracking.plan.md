# Lesson progress tracking — implementation plan

**Status:** Planned (not shipped). **Scope:** RDS-backed lesson progress for enrolled students; dedicated progress API; HTML5 `<video>` client. Aligns with `roadmap.md` (“Progress Tracking v2”) and extends MVP catalog (`design.md` today lists progress as out of scope until this ships).

---

## Goals

- Students see **lesson completion**, **course % complete**, and **resume position** for MP4 playback.
- **Authz:** Same enrollment (+ Cognito when enforced) as `GET /playback/...`; no IDOR across users or courses.
- **Denominator for % complete:** **Video-ready lessons only** (`video_status` ready); incomplete uploads do not block 100%.
- **Completion semantics (server-authoritative):** The **service layer** sets `completed = true` when a persisted **`last_position_sec`** crosses a **configured completion ratio** against **`lessons.duration`** from the DB (see below), and when the client sends **`markComplete: true`** (explicit). **`last_position_sec`** may be updated while `completed = true` (rewatch). **Scrubbing never** sets `completed` to false. **`markIncomplete`** is the only way to clear completion.
- **`markIncomplete` UX:** **No confirmation dialog**; one control triggers `PUT` with `markIncomplete: true`. **No completion history** (no extra columns or audit table for prior `completed_at` values).
- **Reads:** **Dedicated** `GET /courses/{courseId}/progress` (not embedded in `GET /courses/{id}` or lesson list).

---

## Who marks complete: server-authoritative (dumb client)

**Product direction:** The **frontend only reports** `lastPositionSec` (throttled) and optional **`markComplete`** / **`markIncomplete`**; the **service layer** is **authoritative** for `completed`. UI reads **GET progress** only—no local “percent complete” business rules.

### Service rules (single implementation)

On **`PUT .../progress`** (same request may include `lastPositionSec` and/or flags):

1. **Persist** `last_position_sec` when provided (subject to throttle / cap vs `lessons.duration` + slack from DB).
2. **After persist**, set **`completed = true`** (and `completed_at` when newly true) if **either**:
   - **`markComplete: true`** in the body (explicit client signal—covers **`lessons.duration == 0`**, unreliable duration, or “send flag on `ended` only” wiring), **or**
   - **`lessons.duration > 0`** and **`last_position_sec / duration ≥ PROGRESS_COMPLETE_RATIO`** (constant in **`config.py`** / optional env, e.g. **0.92**—**not** reimplemented in the SPA).
3. **Never** set `completed` false from position or from `markComplete` (scrubbing backward only changes resume time).
4. **`markIncomplete: true`** → `completed = false`, `completed_at = null` (position unchanged unless the same request includes a new `lastPositionSec`).

**Frontend (dumb):** Emit `timeupdate` → PUT `lastPositionSec`; on **`ended`**, send **`markComplete: true`** (often with final position). **Do not** compute “am I done?” for persistence—that is **GET** after each save or on navigation.

### Flaws and mitigations

| Issue | Severity | Mitigation / acceptance |
|-------|-----------|-------------------------|
| **`duration` wrong or 0 in DB** | High for ratio-only | **`markComplete`** on `ended` must work; optional duration backfill later; document in ADR. |
| **Trust / spoofing** | Medium (MVP) | Any caller who may PUT can set a high `last_position_sec` or `markComplete`. Same **trust class** as instructor “video ready” without transcoding—acceptable until anti-cheat is required. |
| **Scrub-to-end completes without watching** | Product | Jumping the scrubber past the ratio **will** complete. Accept, or add costly heuristics (not recommended for v1). **`markIncomplete`** is the escape hatch. |
| **Last PUT drops before threshold** | Low | **`markComplete`** on `ended` closes the gap when linear watch does not land exactly past ratio. |
| **Two ways to set complete** (ratio + flag) | Low | One service function; both idempotent toward `completed = true`; unit tests fix ordering. |

**Concrete sequence**  
`duration = 120`, ratio `0.92`.

1. `PUT { "lastPositionSec": 60 }` → stored, `completed` false.  
2. `PUT { "lastPositionSec": 115 }` → stored, **`completed` true** (115/120 ≥ 0.92).  
3. Rewatch: `PUT { "lastPositionSec": 10 }` → stored, **`completed` stays true**.  
4. `PUT { "markIncomplete": true }` → `completed` false.

**Edge:** `duration = 0` → ratio never fires; client **`markComplete`** on `ended` (or operator fixes duration).

---

## Progress requires Cognito (no `auth_enforced=false` branch for this feature)

**Product decision:** Lesson progress **does not** define special behavior when `COGNITO_AUTH_ENABLED=false`. Progress **GET** and **PUT** return the same class of response as **`GET /users/me`** when auth is not configured: **`503`** with body **`code: auth_not_configured`** (reuse message pattern: progress requires a Cognito-backed API). **No** synthetic empty payloads, **no** `progress_requires_auth`, **no** “JWT present but flag false” exception for progress.

**Prerequisite:** Any environment that ships progress must deploy the API stack **with** `CognitoUserPoolArn` so `COGNITO_AUTH_ENABLED=true` (see `api-stack.yaml`). Open-catalog-only stacks simply do not expose usable progress.

### Why `auth_enforced=false` still exists elsewhere in the catalog (deep dive)

Removing the flag **from the whole Lambda** is **not** the same as simplifying the progress plan: today the flag is the **switch for “optional Cognito” MVP** across course management, not a progress-only quirk.

**1. IaC sets the flag from whether a pool ARN was passed**

```107:107:infrastructure/templates/api-stack.yaml
  HasCognitoAuthorizer: !Not [!Equals [!Ref CognitoUserPoolArn, '']]
```

```271:271:infrastructure/templates/api-stack.yaml
          COGNITO_AUTH_ENABLED: !If [HasCognitoAuthorizer, 'true', 'false']
```

When `CognitoUserPoolArn` is empty, protected API methods use **`AuthorizationType: NONE`** (grep the template: `!If [HasCognitoAuthorizer, COGNITO_USER_POOLS, NONE]`). The Lambda still runs; it must behave sanely with **no gateway authorizer** and often **no JWT** on the request.

**2. Handler passes the same flag into both controllers**

```93:109:infrastructure/lambda/catalog/index.py
                if method == "GET" and parts == ["users", "me"]:
                    response = handle_users_me(
                        event,
                        origin=origin,
                        auth_svc=auth_service,
                        auth_enforced=cfg.cognito_auth_enabled,
                        jwt_config=jwt_config,
                    )
                else:
                    response = course_management_handle(
                        event,
                        origin=origin,
                        svc=service,
                        video_bucket=cfg.video_bucket,
                        auth_svc=auth_service,
                        auth_enforced=cfg.cognito_auth_enabled,
                        jwt_config=jwt_config,
                    )
```

**3. `/users/me` explicitly refuses work when auth is off**

```33:41:infrastructure/lambda/catalog/services/auth/controller.py
    if not auth_enforced:
        return json_response(
            503,
            {
                "message": "User profile requires Cognito authorizer on API Gateway.",
                "code": "auth_not_configured",
            },
            origin,
        )
```

**4. Course controller: “authenticated” checks are no-ops when auth is off**

```71:76:infrastructure/lambda/catalog/services/course_management/controller.py
def _require_authenticated(auth_enforced: bool, claims: Dict[str, Any]) -> None:
    if not auth_enforced:
        return
    if not _actor_sub(claims):
        raise Unauthorized("Authentication required")
```

So routes that call `_require_authenticated` **do not** demand a user when the stack has no Cognito.

**5. Service layer: open mode for catalog + playback vs locked mode**

- **Anyone can view lesson/playback path for published courses** when auth is not enforced (no enrollment, no login):

```185:197:infrastructure/lambda/catalog/services/course_management/service.py
    def ensure_can_view_lessons_and_playback(
        self,
        course_id: str,
        *,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> Course:
        course = self._repo.get_course(course_id)
        if not course:
            raise NotFound("Course not found")
        if not auth_enforced:
            return course
```

- **`viewer_has_lesson_access`** returns **True** for everyone when `auth_enforced` is false (so “enrolled” semantics collapse to “world can see published”):

```166:176:infrastructure/lambda/catalog/services/course_management/service.py
    def viewer_has_lesson_access(
        self,
        course: Course,
        *,
        course_id: str,
        cognito_sub: str,
        role: str,
        auth_enforced: bool,
    ) -> bool:
        if not auth_enforced:
            return True
```

- **Course detail** reports `enrolled: true` for all callers when auth is off (because `has_lessons` is forced true):

```217:225:infrastructure/lambda/catalog/services/course_management/service.py
        if auth_enforced:
            if course.status == "DRAFT":
                if not self._can_manage_course_unenrolled(course, cognito_sub=cognito_sub, role=role):
                    raise NotFound("Course not found")
            has_lessons = self.viewer_has_lesson_access(
                course, course_id=course_id, cognito_sub=cognito_sub, role=role, auth_enforced=auth_enforced
            )
        else:
            has_lessons = True
```

- **Instructor dashboard** `GET /courses/mine` lists **every course** in the catalog when auth is off (no sub filter):

```124:125:infrastructure/lambda/catalog/services/course_management/service.py
        if not auth_enforced:
            courses = self._repo.list_courses()
```

- **Mutations** skip teacher/ownership checks when auth is off:

```256:258:infrastructure/lambda/catalog/services/course_management/service.py
        if not auth_enforced:
            return
```

**Point of all that:** the **`false` branch is the “catalog API without identity” deployment mode**: browse + watch published content + call mutating endpoints **without** Cognito (explicitly described in `design.md` as optional auth for demos). It is **not** integ-test-only; it is any API stack deployed **without** `CognitoUserPoolArn`.

**If you “remove the false branch completely” from the whole codebase**, you are really saying: **Cognito is mandatory for every API deployment** — template would always attach the authorizer, Lambda would always enforce JWT + roles, and you would **delete** the open-demo behavior above (and update `design.md`, deploy scripts, and many tests). That is a **large product/IaC change**, separate from lesson progress.

**For lesson progress only:** we do **not** implement open-mode semantics; we align with **`/users/me`** and return **503 `auth_not_configured`** when `auth_enforced` is false.

### Progress auth matrix (final)

| `auth_enforced` | Caller | GET `/courses/{id}/progress` | PUT `.../progress` |
|-----------------|--------|------------------------------|---------------------|
| `false` | any | **503** `auth_not_configured` | **503** `auth_not_configured` |
| `true` | no / invalid JWT | **401** | **401** |
| `true` | JWT, not enrolled | **403** `enrollment_required` | **403** |
| `true` | JWT, enrolled | **200** | **200** / **204** |

---

## Data model (RDS)

New table `lesson_progress` (names follow `001_initial_schema.sql` conventions; Python adapters map camelCase as today):

- `user_sub` (FK `users`), `lesson_id` (FK `lessons`), `course_id` (FK `courses`, denormalized for queries)
- `completed` BOOLEAN NOT NULL DEFAULT FALSE
- `completed_at` TIMESTAMPTZ NULL
- `last_position_sec` INTEGER NOT NULL DEFAULT 0, CHECK (>= 0)
- `updated_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
- PRIMARY KEY (`user_sub`, `lesson_id`); index on (`course_id`, `user_sub`)

**CASCADE** with lessons/courses so rows do not orphan.

**DynamoDB:** Deployed dev/prod are RDS-only; document “progress N/A or no-op” for legacy `USE_RDS=false` unless product explicitly dual-writes.

---

## API

| Method | Path | Body / behavior |
|--------|------|-----------------|
| GET | `/courses/{courseId}/progress` | Returns per-lesson progress + rollup: `completedCount`, `totalReadyLessons`, `percentComplete`, `lessons: [{ lessonId, completed, completedAt?, lastPositionSec }]` |
| PUT | `/courses/{courseId}/lessons/{lessonId}/progress` | JSON: optional `lastPositionSec`; optional `markComplete: true`; optional `markIncomplete: true`. **400** if both marks in one request. **Service** sets `completed` when ratio satisfied (see **Who marks complete**) or when `markComplete: true`. Idempotent toward completed. |

**Rules:** **503** `auth_not_configured` when `not auth_enforced` (same product stance as **`GET /users/me`**). When `auth_enforced`, enrollment required for GET/PUT (mirror playback). 404 for wrong course/lesson or hidden draft; throttle position-only writes; optional cap `lastPositionSec` vs `lessons.duration` + slack when duration > 0.

**Rollup:** `percentComplete = completedReadyCount / totalReadyLessons` where a ready lesson counts as completed only if progress row has `completed = true`.

---

## Lambda layout

New bounded context `infrastructure/lambda/catalog/services/progress/` (`ports.py`, `service.py`, `rds_repo.py`, `controller.py`, `contracts.py`) per `plans/architecture/module-map.md` and `.cursor/rules/clean-architecture-boundaries.mdc`. Wire in `bootstrap.py` / `index.py`; extend `scripts/check_lambda_boundaries.py` if new paths require allowlisting. Register routes in `infrastructure/templates/api-stack.yaml` (and OPTIONS) consistent with existing patterns.

---

## Frontend

- `frontend/src/lib/api.ts`: typed client for GET/PUT progress.
- `LessonPlayerPage.tsx`: load **GET progress** for UI; throttled PUT **`lastPositionSec`**; on **`ended`** send **`markComplete: true`**; **`markIncomplete`** without confirmation; if **GET/PUT progress** returns **503** `auth_not_configured`, hide progress UI (same as environments without Cognito-backed profile).
- Course / lesson list UI: completion indicators from **GET progress** (separate fetch), not from lesson list payload.

---

## Implementation order (TDD — mandatory)

Execute in **vertical slices** (Red → Green → Refactor per slice). Do not merge production code without tests that failed before the change.

### Slice A — persistence contract

1. **Red:** Unit test on `ProgressRdsRepository` (or equivalent) for upsert/select: insert progress, update `last_position_sec`, set complete, `markIncomplete` clears `completed`/`completed_at` without requiring row delete.
2. **Green:** Migration `002_*.sql` + repo implementation.
3. **Refactor:** Names, SQL clarity, keep boundaries.

### Slice B — service rules

1. **Red:** Service tests: threshold from DB `duration` + ratio sets `completed`; `markComplete` sets complete when `duration == 0`; `markIncomplete` clears; post-complete position updates; enrolled-only; mutually exclusive marks **400**; spoofed high `last_position_sec` completes (document as accepted MVP trust).
2. **Green:** `ProgressService` + enrollment port integration.
3. **Refactor.**

### Slice C — HTTP adapter

1. **Red:** Controller tests: **503** `auth_not_configured` when `auth_enforced=False` for GET and PUT progress (mirror `handle_users_me` contract); **401**/ **403** / **200** shapes when `auth_enforced=True`.
2. **Green:** Controller + routing + CloudFormation method.
3. **Refactor.**

### Slice D — frontend

1. **Red:** Vitest for API wrapper parsing/validation or player hook behavior (throttle / mark complete path) with fetch mocked.
2. **Green:** UI wiring.
3. **Refactor.**

### Slice E — integration

- `tests/integration/test_rds_path.py` (or new file): progress endpoints against real RDS test harness if pattern exists; else document reliance on unit + deploy smoke.

**CI:** Match `AGENTS.md` — frontend `npm run test` / lint / build; root `python scripts/check_lambda_boundaries.py`, vulture as applicable.

---

## Parallel execution

Independent streams after **Slice A** migration + repo is merged or branched:

| Stream | Work | Depends on |
|--------|------|------------|
| Backend B+C | Service + controller + API Gateway YAML | Slice A repo + migration |
| Frontend D | `api.ts` + player UI | Stable DTOs from contracts (can mock until API deployed) |

**Aggregation:** Single PR or ordered merges: **A → (B+C and D in parallel) → E**; resolve contract drift in a short “integration” sub-step before merge.

**Note for implementers:** For large follow-ups, Cursor **Task** tool may be used for parallel **implementation** subagents only where the repo allows—each subagent must return **contract summary + file list** for the parent to merge. **Do not** use Task to run `/review_plan` itself.

---

## Documentation (post-success)

After the feature is implemented and verified:

1. Invoke **`/update_docs`** per `.cursor/skills/update-docs/SKILL.md`: read `AGENTS.md` and `design.md` first; update **`design.md`** (API §7, data §6, FR table—move progress in-scope); **`roadmap.md`** only if baseline vs Phase 2 wording must change; **`ImplementationHistory.md`** with dated entry and file links.
2. Add **`plans/architecture/adr-NNNN-lesson-progress.md`** (next free number per `.cursor/rules/adr-standards.mdc`) for schema + authz + dedicated API choice.
3. Update **`plans/architecture/module-map.md`** with `services/progress/`.

---

## Peer review

**Verdict:** Approve with revisions embedded above.

| Area | Assessment |
|------|------------|
| Goals vs steps | Clear; implementation slices map to acceptance. |
| TDD | Original chat plan lacked explicit Red/Green order—**fixed** in Implementation order. |
| Context rot | Moderate-sized feature; parallel backend/frontend after repo slice is sufficient (no 8+ step single-agent laundry list). |
| Contradictions | None: dedicated GET + PUT align with “no embed on course.” |
| Scope | Dynamo dual-write explicitly de-scoped for prod. |
| Verifiability | Rollup math and authz cases have named test targets. |
| Repo fit | Paths match `AGENTS.md`, `module-map.md`, `api-stack.yaml`, `LessonPlayerPage.tsx`. |

**Gaps addressed in this document:** Explicit `markIncomplete`; post-complete position updates; ready-only denominator; `/update_docs` + ADR + module-map closure.

---

## Security audit

No design is “100% secure.” Residual risk remains (token theft, client spoofed positions).

| Control | Notes |
|---------|--------|
| **Authn** | Progress: **503** when `not auth_enforced` (Cognito not configured). When enforced, JWT + enrollment as today. |
| **Authz / IDOR** | Every read/write scoped by `user_sub` from token + enrollment check on `courseId`/`lessonId`; align with playback service checks. |
| **Input validation** | Strict JSON at boundary; reject negative time; reject dual marks; bound `lastPositionSec` vs duration to limit garbage/abuse. |
| **Rate limiting** | Application throttle on position writes; API Gateway stage limits already exist—document not relying on position spam for DoS against DB. |
| **PII** | Progress rows are not email-bearing; still protect logs from dumping positions at DEBUG. |
| **CSRF** | SPA + API: same patterns as existing authenticated `fetch` (Bearer); no new cookie-based session introduced by this plan. |
| **Multi-tenant** | `user_sub` + `course_id` composite enforcement prevents cross-user reads/writes. |

**Before merge:** Confirm integration tests or manual checklist for “enrolled user A cannot read/write course B progress.”

---

## Test plan (TDD)

| Layer | Must cover |
|-------|------------|
| Repo | Upsert, complete, incomplete, position update, cascade assumption (or migration FK). |
| Service | Enrollment gate, 404 mapping, mark exclusivity, post-complete position updates. |
| HTTP | GET/PUT status codes, response shape. |
| Frontend | API client + critical player paths (mocked fetch). |
| Regression | Any bugfix ships with failing test first. |

**Explicit non-goals for test:** Full browser E2E (no Playwright in default CI); optional manual smoke after deploy.

---

## Resolved product decisions

| Topic | Decision |
|-------|----------|
| **`markIncomplete` UX** | No confirmation; no completion history columns or audit trail. |
| **Completion authority** | **Server-authoritative:** `completed` becomes true when **`last_position_sec / lessons.duration ≥ PROGRESS_COMPLETE_RATIO`** (from DB duration) **or** when **`markComplete: true`**; **`markIncomplete`** clears. Client does not implement ratio logic. |
| **Auth / Cognito** | Progress unavailable without Cognito-backed API (**503**); no synthetic progress. Removing **`auth_enforced=false` from the entire catalog** is a separate initiative (would end open-demo mutations + anonymous playback per current service code). |

---

## Changelog

- **2026-05-05:** Plan consolidated from design discussion; `/review_plan` skill applied (peer review, security, TDD, parallelization, `/update_docs`).
- **2026-05-05:** Progress: removed synthetic `auth_enforced=false` behavior; **503** only; added **deep dive** on why the flag exists catalog-wide vs progress scope.
