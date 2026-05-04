# ADR: Enrollment rows and course view access

## Context

Published courses should be discoverable without sign-in, but lesson lists and playback require either enrollment or instructor/admin override.

## Decision

- Store enrollments in the existing catalog table: `PK = USER#<sub>`, `SK = ENROLLMENT#<courseId>`.
- Add `GET /courses/{id}/preview` (no Cognito at gateway) returning published metadata plus `lessonsPreview` only.
- Gate `GET /courses/{id}`, `GET .../lessons`, and `GET /playback/...` in Lambda when `COGNITO_AUTH_ENABLED` is true, with admin and course owner (same ownership rule as mutations) bypassing enrollment.

## Consequences

- API Gateway must attach the Cognito authorizer to the protected GETs when a pool is configured; anonymous clients use `/preview` only.
- Deleting a course does not automatically delete enrollment rows (acceptable for MVP; rows are small and inert).
