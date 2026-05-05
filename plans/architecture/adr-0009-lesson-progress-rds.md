# ADR 0009 — Lesson progress on RDS (student resume + completion)

**Status:** Accepted (MVP extension)

## Context

Students need to resume MP4 playback and see course completion without inventing parallel client state. Progress must respect enrollment and identity when Cognito is enforced, align with the RDS-first catalog ([ADR-0008](./adr-0008-dynamodb-to-rds-migration.md)), and stay out of the deprecated DynamoDB catalog path.

## Decision

- Add PostgreSQL table `lesson_progress` ([`002_lesson_progress.sql`](../../infrastructure/database/migrations/002_lesson_progress.sql)): `(user_sub, lesson_id)` primary key, denormalized `course_id`, `completed`, `completed_at`, `last_position_sec`, `updated_at`.
- New bounded context `services/progress/`: `LessonProgressService` owns authorization (enrolled or can manage course), completion rules (server ratio from `PROGRESS_COMPLETE_RATIO`, optional explicit `markComplete`, `markIncomplete` clears), and persistence via `LessonProgressRdsRepository`.
- HTTP: `GET /courses/{courseId}/progress`, `PUT /courses/{courseId}/lessons/{lessonId}/progress` — routed from `index.py` when `USE_RDS=true` wires `progress_service`; **503** `progress_requires_rds` on DynamoDB-only stacks; **503** `auth_not_configured` when `COGNITO_AUTH_ENABLED=false` (matches `/users/me`).
- API Gateway: Cognito authorizer on GET progress and PUT lesson progress when a pool ARN is supplied; OPTIONS stays open.
- Frontend: `LessonPlayerPage` loads progress after successful playback fetch, resumes `lastPositionSec`, throttled position PUTs, `ended` sends `markComplete`, **Mark lesson as not done** calls `markIncomplete`.

## Consequences

- Operators must apply migration `002_lesson_progress.sql` to RDS (same path as `001`; schema apply Lambda splits statements).
- Progress is **not** available on `USE_RDS=false` deployments; UI degrades gracefully.
- Completion denominator is **video-ready lessons only** (matches product contract).

## Alternatives considered

- **DynamoDB progress items:** Rejected for deployed dev/prod — catalog traffic is RDS-only; avoids dual-write.
- **Embed progress in GET /courses/{id}/lessons:** Rejected — dedicated read keeps payloads stable and matches a clear API contract.
