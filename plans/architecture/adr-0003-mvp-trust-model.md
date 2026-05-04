# ADR 0003 — MVP trust model (no end-user auth)

## Status

Accepted (MVP)

## Context

The MVP intentionally ships without student/instructor authentication.

## Decision

Treat the API as **public** with coarse protections:

- Operational guardrails (CORS allowlist per environment, throttling later).
- Business rules enforced in the service layer (e.g., publish requires a ready lesson).

## Consequences

- Anyone who can reach the API can invoke mutating endpoints unless additional controls are added.
- UI must not imply strong ownership guarantees.

## Mitigations (non-blocking)

- Add auth (ADR 0004) before exposing sensitive instructor workflows broadly.
- Add abuse controls (WAF / usage plans) if the endpoint becomes public on the internet.
