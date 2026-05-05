# ADR: Enrollment rows and course view access

## Context

Published courses should be discoverable without sign-in, including **lesson list metadata** (titles, order, thumbnails) for catalog UI; **playback** still requires enrollment or instructor/admin override when auth is enforced.

## Decision

- Store enrollments in the existing catalog table: `PK = USER#<sub>`, `SK = ENROLLMENT#<courseId>`.
- **`GET /courses/{id}`** and **`GET /courses/{id}/lessons`** use **no** Cognito authorizer at API Gateway (`AuthorizationType: NONE`). Lambda returns **PUBLISHED** catalog data (including presigned **thumbnail** URLs; **`videoKey`** never in JSON). **DRAFT** returns **404** unless the caller is owner/admin (JWT claims when present). **`enrolled`** on course detail is **false** for anonymous or not-yet-enrolled viewers on published courses.
- **`GET /playback/...`** remains Cognito-gated at the gateway when a pool is configured; Lambda enforces enrollment (or owner/admin bypass) when `COGNITO_AUTH_ENABLED` is true.

## Consequences

- Anonymous browsers call the same course + lesson list endpoints as signed-in users; only playback requires auth + enrollment when enforced.
- Supersedes the earlier **`GET /courses/{id}/preview`** + **`lessonsPreview`** shape (removed).
- Deleting a course does not automatically delete enrollment rows (acceptable for MVP; rows are small and inert).
