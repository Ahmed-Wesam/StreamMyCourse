# ADR 0010 — Lesson Progress Tracking with PostgreSQL RDS

## Status

Accepted (MVP)

## Context

We need per-student lesson progress tracking (completed status, resume position) for the StreamMyCourse platform. The feature must:

- Track which lessons each student has completed
- Store last video position for resume functionality
- Calculate course completion percentage
- Support explicit mark complete/incomplete actions
- Work only when PostgreSQL RDS is enabled (USE_RDS=true)

## Decision

We will implement progress tracking as an RDS-only feature using PostgreSQL.

### Backend Architecture

- **Clean Architecture**: Controller → Service → Repository layering
- **Location**: `services/progress/` bounded context
- **Storage**: PostgreSQL via `lesson_progress` table
- **API Endpoints**:
  - GET /courses/{courseId}/progress - Get full course progress
  - PUT /courses/{courseId}/lessons/{lessonId}/progress - Update lesson progress

### Key Design Choices

1. **RDS-Only**: Progress tracking requires PostgreSQL. When USE_RDS=false, API returns 503 with code `progress_requires_rds`. This simplifies implementation and aligns with the platform's move toward RDS as primary persistence.

2. **Auto-Completion**: Lessons auto-complete when position/duration >= 0.92 (configurable via CloudFormation). This provides good UX without requiring explicit user action.

3. **Position Slack**: Allow reporting position up to 30 seconds past video duration to handle timing mismatches between client and server.

4. **Authorization**: Users must be enrolled in course OR be the course teacher/owner. Prevents IDOR attacks by always filtering by user_sub.

5. **No Throttling (MVP)**: Rate limiting deferred to future phase. Current implementation accepts all updates.

### Database Schema

Canonical idempotent DDL (`CREATE TABLE IF NOT EXISTS`, indexes, check constraint) lives in [`infrastructure/database/migrations/001_initial_schema.sql`](../../infrastructure/database/migrations/001_initial_schema.sql). The following snippet summarizes shape and relationships.

```sql
CREATE TABLE lesson_progress (
    user_sub VARCHAR(255) NOT NULL REFERENCES users(user_sub),
    lesson_id UUID NOT NULL REFERENCES lessons(id),
    course_id UUID NOT NULL REFERENCES courses(id),
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    last_position_sec INTEGER DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_sub, lesson_id)
);
```

### Frontend Integration

- Progress loads after successful playback URL fetch
- 12-second throttled position updates during playback
- Video ended event triggers markComplete
- Visual indicators: course progress bar, "Done" badges, "Mark as not done" button

## Consequences

### Pros

- Consistent with existing RDS-first architecture
- Simple, queryable relational model (no DynamoDB single-table complexity)
- Supports efficient "get all progress for user in course" lookups via index
- Clean separation via bounded context

### Cons

- Feature unavailable for DynamoDB-only deployments (must migrate to RDS)
- Additional database table to maintain
- No global rate limiting (deferred to future)

## Alternatives Considered

### DynamoDB Single-Table

Rejected: Would require complex PK/SK design (USER#sub/PROGRESS#course#lesson) and duplicate effort when RDS is becoming primary.

### Separate Progress Microservice

Rejected: MVP scope; additional operational complexity not justified for one feature.

### Client-Only Progress

Rejected: Resume position and completion status must persist across devices.

## Follow-ups

- Future: Add rate limiting/throttling configuration
- Future: Teacher dashboard viewing student progress
- Future: Progress analytics (time spent, re-watching patterns)

## Related

- [ADR 0008 — DynamoDB-to-RDS PostgreSQL migration](./adr-0008-dynamodb-to-rds-migration.md)
- [`design.md`](../../design.md) §7 (API)
- [`plans/architecture/module-map.md`](./module-map.md)
