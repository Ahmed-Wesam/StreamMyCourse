# ADR 0004 — Future authentication boundary

## Status

Proposed

## Context

Authentication will eventually be required for instructor workflows and for safe multi-tenant behavior.

## Decision (default recommendation)

Prefer **API Gateway authorizers** (JWT/Cognito) for request authentication, keeping the Lambda focused on authorization checks based on claims.

Alternate (acceptable for small APIs): implement auth endpoints/controllers under `services/auth/` with strict separation from `course_management/`.

## Consequences

- Clear separation between “who you are” (gateway) vs “what you can do” (service rules).
- Requires an ADR update when the concrete provider is chosen (Cognito vs custom JWT).
