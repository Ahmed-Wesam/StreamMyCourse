# ADR 0006 — DynamoDB access pattern evolution (Scan → Query/GSI)

## Status

Proposed (do not implement until driven by real access/auth needs)

## Context

The MVP uses a `Scan` filtered to course metadata items to list courses. This is acceptable at tiny scale but becomes costly and slow as the table grows.

## Decision

Defer access-pattern optimization until:

- course counts / traffic justify it, and
- instructor identity exists (so “my courses” is meaningful), and/or
- public catalog needs efficient “published-only” listing.

## Options (choose later)

1. **GSI1** for published catalog projection (e.g., `GSI1PK=PUBLISHED`, `GSI1SK=updatedAt`) with sparse items.
2. **GSI per instructor** once auth exists (e.g., `INSTRUCTOR#<id>` → courses).
3. Replace “list all courses” with curated feeds (admin tooling) if the product direction changes.

## Consequences

- IAM should drop `dynamodb:Scan` once no code path uses `Scan`.
- Any new GSI must be accompanied by a data backfill/migration plan.

## Acceptance trigger

Implement when either:

- p95 `ListCourses` latency/cost becomes a problem, or
- auth requires new query patterns that cannot be satisfied efficiently with `Scan`.
