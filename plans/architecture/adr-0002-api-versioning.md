# ADR 0002 — Public HTTP API versioning strategy (MVP)

## Status

Accepted (MVP)

## Context

The API is exposed via API Gateway paths under a stage (e.g. `/dev`). Clients include a browser SPA.

## Decision

- Prefer **additive** changes (new fields, new endpoints) over breaking changes.
- Avoid renaming/removing fields without a coordinated client release.
- If a breaking change becomes necessary, introduce a **new path prefix** or a new stage and migrate clients explicitly.

## Consequences

- Safer iteration for a small team without heavy versioning machinery.
- Requires discipline in PR review (“is this additive?”).
